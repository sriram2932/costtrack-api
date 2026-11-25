"""CostTrack API — working implementation.

Implements the API described in the costtrack-api-docs repo: four endpoints
for reading a priced bill of quantities, submitting a cost estimate as a
draft, and getting a rolled-up project cost summary. Same project, same
data, same error codes as the API reference.

Auth: Bearer token in the Authorization header. The demo token is
``demo-token-2026`` unless COSTTRACK_API_TOKEN is set. Rate limit: 100
requests per minute per token (COSTTRACK_RATE_LIMIT overrides it).

Run it:
    uvicorn app.main:app --reload
Then open http://127.0.0.1:8000/docs for the interactive API docs.
"""

import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import store

API_VERSION = "1.1.0"
API_TOKEN = os.environ.get("COSTTRACK_API_TOKEN", "demo-token-2026")
RATE_LIMIT = int(os.environ.get("COSTTRACK_RATE_LIMIT", "100"))
RATE_WINDOW_SECONDS = 60
SGT = timezone(timedelta(hours=8))

app = FastAPI(
    title="CostTrack API",
    version=API_VERSION,
    description=(
        "Bill-of-quantities and cost-estimation API for construction projects. "
        "Read a project's priced BOQ, submit a cost estimate as a draft for "
        "review, and get a rolled-up cost summary by trade."
    ),
)

# ---------------------------------------------------------------------------
# Errors: the API reference error shape for every endpoint.
# {"error": {"code": "...", "message": "...", "field": "..." (when named)}}
# ---------------------------------------------------------------------------


class ApiError(Exception):
    def __init__(self, status, code, message, field=None, headers=None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.field = field
        self.headers = headers or {}


@app.exception_handler(ApiError)
async def api_error_handler(request, exc):
    body = {"error": {"code": exc.code, "message": exc.message}}
    if exc.field is not None:
        body["error"]["field"] = exc.field
    return JSONResponse(status_code=exc.status, content=body, headers=exc.headers)


def _field_path(loc):
    """Pydantic loc tuple to the docs' field path, e.g. items[0].quantity."""
    parts = [p for p in loc if p not in ("body", "query")]
    out = ""
    for part in parts:
        if isinstance(part, int):
            out += f"[{part}]"
        else:
            out = f"{out}.{part}" if out else str(part)
    return out or "request"


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, exc):
    """Translate Pydantic validation errors into the API reference codes."""
    err = exc.errors()[0]
    field = _field_path(err.get("loc", []))
    err_type = err.get("type", "")
    leaf = field.split(".")[-1].split("[")[0]

    if err_type == "missing":
        code, message = "missing_field", f"{field} is required."
    elif err_type == "string_too_short":
        code, message = "missing_field", f"{field} is required."
    elif err_type == "string_too_long":
        code, message = "invalid_field", err.get("msg", f"{field} is too long.")
    elif err_type == "too_short":
        code, message = "missing_field", "At least one BOQ item is required."
    elif leaf == "quantity":
        code, message = "invalid_quantity", "quantity must be greater than 0."
    elif leaf == "rate":
        code, message = "invalid_rate", "rate must be 0 or greater."
    elif err_type in ("greater_than", "greater_than_equal", "less_than_equal", "less_than"):
        code, message = "invalid_field", err.get("msg", f"{field} is out of range.")
    else:
        code, message = "invalid_field", err.get("msg", f"{field} is invalid.")
    body = {"error": {"code": code, "message": message, "field": field}}
    return JSONResponse(status_code=400, content=body)


# ---------------------------------------------------------------------------
# Auth and rate limiting
# ---------------------------------------------------------------------------

_hits = {}


def check_rate_limit(token):
    now = time.time()
    hits = [t for t in _hits.get(token, []) if now - t < RATE_WINDOW_SECONDS]
    if len(hits) >= RATE_LIMIT:
        retry_after = int(RATE_WINDOW_SECONDS - (now - hits[0])) + 1
        raise ApiError(
            429,
            "rate_limited",
            f"Too many requests. Retry after {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )
    hits.append(now)
    _hits[token] = hits


def require_token(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise ApiError(401, "unauthorized", "Missing, expired or revoked token.")
    token = auth[len("Bearer "):].strip()
    if not token or not secrets.compare_digest(token, API_TOKEN):
        raise ApiError(401, "unauthorized", "Missing, expired or revoked token.")
    check_rate_limit(token)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class BoqItem(BaseModel):
    item_no: str
    description: str
    unit: str
    quantity: float
    rate: float
    amount: float
    trade: str


class BoqItemDetail(BoqItem):
    updated_at: str


class BoqList(BaseModel):
    project_id: str
    currency: str
    page: int
    per_page: int
    total_items: int
    items: list[BoqItem]


class EstimateItemIn(BaseModel):
    description: str = Field(..., min_length=1)
    unit: str = Field(..., min_length=1)
    quantity: float = Field(..., gt=0)
    rate: float = Field(..., ge=0)


class EstimateIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    items: list[EstimateItemIn] = Field(..., min_length=1)
    notes: str | None = Field(default=None, max_length=1000)


class EstimateOut(BaseModel):
    estimate_id: str
    project_id: str
    title: str
    status: str
    total_amount: float
    currency: str
    created_at: str


class TradeTotal(BaseModel):
    trade: str
    total: float


class DraftEstimate(BaseModel):
    estimate_id: str
    total_amount: float


class CostSummary(BaseModel):
    project_id: str
    currency: str
    live_total: float
    by_trade: list[TradeTotal]
    draft_estimate: DraftEstimate | None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _money(value):
    return float(Decimal(str(value)).quantize(Decimal("0.01")))


def _get_project_or_404(project_id):
    project = store.get_project(project_id)
    if project is None:
        raise ApiError(404, "not_found", f"Project {project_id} was not found.")
    return project


def _public_item(item):
    return {k: item[k] for k in ("item_no", "description", "unit", "quantity", "rate", "amount", "trade")}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/")
def service_info():
    return {
        "service": "CostTrack API",
        "version": API_VERSION,
        "docs": "/docs",
        "note": "Demo implementation. Data is held in memory and resets on restart.",
    }


@app.get("/projects/{project_id}/boq", response_model=BoqList)
def list_boq_items(
    project_id: str,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=100),
    trade: str | None = Query(default=None),
    _token: None = Depends(require_token),
):
    project = _get_project_or_404(project_id)
    items = project["items"]
    if trade is not None:
        items = [item for item in items if item["trade"] == trade]
    total_items = len(items)
    start = (page - 1) * per_page
    page_items = items[start:start + per_page]
    return {
        "project_id": project_id,
        "currency": project["currency"],
        "page": page,
        "per_page": per_page,
        "total_items": total_items,
        "items": [_public_item(item) for item in page_items],
    }


@app.get("/projects/{project_id}/boq/{item_no}", response_model=BoqItemDetail)
def get_boq_item(project_id: str, item_no: str, _token: None = Depends(require_token)):
    project = _get_project_or_404(project_id)
    for item in project["items"]:
        if item["item_no"] == item_no:
            return item
    raise ApiError(404, "not_found", f"BOQ item {item_no} was not found in project {project_id}.")


@app.post("/projects/{project_id}/estimates", response_model=EstimateOut, status_code=201)
def create_estimate(project_id: str, body: EstimateIn, _token: None = Depends(require_token)):
    project = _get_project_or_404(project_id)
    total = _money(sum(Decimal(str(item.quantity)) * Decimal(str(item.rate)) for item in body.items))
    estimate_id = "est_" + "".join(
        secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6)
    )
    draft = {
        "estimate_id": estimate_id,
        "project_id": project_id,
        "title": body.title,
        "status": "draft",
        "total_amount": total,
        "currency": project["currency"],
        "created_at": datetime.now(SGT).isoformat(timespec="seconds"),
    }
    store.save_draft(project_id, draft)
    return draft


@app.get("/projects/{project_id}/summary", response_model=CostSummary)
def get_project_summary(project_id: str, _token: None = Depends(require_token)):
    project = _get_project_or_404(project_id)
    by_trade = {}
    for item in project["items"]:
        by_trade[item["trade"]] = by_trade.get(item["trade"], Decimal("0")) + Decimal(str(item["amount"]))
    live_total = _money(sum(by_trade.values()))
    draft = store.get_draft(project_id)
    return {
        "project_id": project_id,
        "currency": project["currency"],
        "live_total": live_total,
        "by_trade": [
            {"trade": trade, "total": _money(total)}
            for trade, total in sorted(by_trade.items())
        ],
        "draft_estimate": (
            {"estimate_id": draft["estimate_id"], "total_amount": draft["total_amount"]}
            if draft is not None
            else None
        ),
    }
