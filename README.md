# CostTrack API

I built this to learn how a real cost API works, by writing one. It is a running FastAPI service for bills of quantities and cost estimation, with the same four endpoints, the same data and the same error codes as the CostTrack API docs in the companion [costtrack-api-docs](https://github.com/sriram2932/costtrack-api-docs) repo.

CostTrack is a fictional product, built as a portfolio project. The API is real and runnable; the company behind it is not.

Written by Sriram Balasubramanian, Singapore. Quantity surveyor and AI training specialist, learning Python by building real tools.

## What it does

- `GET /projects/{project_id}/boq`: list a project's priced BOQ items, in bill order, with pagination and a trade filter
- `GET /projects/{project_id}/boq/{item_no}`: get one BOQ item
- `POST /projects/{project_id}/estimates`: submit a cost estimate, saved as a draft for review
- `GET /projects/{project_id}/summary`: rolled-up project cost by trade, with the draft total shown separately

One project is seeded: `proj_01J8X`, 37 BOQ items across concrete, steel and finishes, live total SGD 1,842,500.00. The seed totals match the API reference exactly. Data is held in memory and resets when the server restarts.

## Run it

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000/docs for the interactive API docs, generated from the code.

## Try it

The demo token is `demo-token-2026`. Set `COSTTRACK_API_TOKEN` to use your own.

```bash
export TOKEN="demo-token-2026"

# List the concrete BOQ items
curl "http://127.0.0.1:8000/projects/proj_01J8X/boq?trade=concrete&per_page=2" \
  -H "Authorization: Bearer $TOKEN"

# Get one item
curl http://127.0.0.1:8000/projects/proj_01J8X/boq/3.1 \
  -H "Authorization: Bearer $TOKEN"

# Submit an estimate from the example file
curl -X POST http://127.0.0.1:8000/projects/proj_01J8X/estimates \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @examples/estimate.json

# Check the project summary (the draft shows separately)
curl http://127.0.0.1:8000/projects/proj_01J8X/summary \
  -H "Authorization: Bearer $TOKEN"
```

## Rules the API enforces

- Auth: every `/projects/*` call needs a Bearer token. Missing or wrong token returns `401 unauthorized`.
- Rate limit: 100 requests per minute per token. Over that returns `429 rate_limited` with a `Retry-After` header in seconds. Set `COSTTRACK_RATE_LIMIT` to change it.
- Estimates: `quantity` must be greater than 0 (`invalid_quantity`), `rate` must be 0 or greater (`invalid_rate`), required fields must be present (`missing_field`). A title over 120 characters or notes over 1,000 characters returns `invalid_field`; that code is an addition to the API reference error table. If any item fails validation, the whole estimate is rejected and nothing is saved.
- Amounts: `amount` is always `quantity x rate`, rounded to 2 decimal places. The summary `by_trade` totals always add up to `live_total`.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

17 tests cover the four endpoints, pagination, the trade filter, draft estimates, every documented error code, auth and the rate limit.

## Project structure

```text
costtrack-api/
  app/
    main.py    FastAPI app: endpoints, auth, rate limiting, error handling
    seed.py    Seeded project and BOQ items (37 items, totals match the docs)
    store.py   In-memory store for the project and draft estimates
  tests/
    test_api.py
  examples/
    estimate.json
```

## Status

Working demo, November 2026. In-memory storage only, single demo token, no database. Good enough to run, test and show; not built for production traffic.
