"""Tests for the CostTrack API.

Run from the repo root:
    pytest
"""

import pytest
from fastapi.testclient import TestClient

from app import main, store

TOKEN = "demo-token-2026"
PROJECT = "proj_01J8X"


@pytest.fixture()
def client():
    store.reset()
    with TestClient(main.app) as test_client:
        yield test_client


def auth_headers(token=TOKEN):
    return {"Authorization": f"Bearer {token}"}


def test_service_info(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "CostTrack API"


def test_list_boq_matches_reference(client):
    response = client.get(f"/projects/{PROJECT}/boq", headers=auth_headers())
    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == PROJECT
    assert body["currency"] == "SGD"
    assert body["total_items"] == 37
    first = body["items"][0]
    assert first == {
        "item_no": "3.1",
        "description": "Grade 40 reinforced concrete, columns",
        "unit": "m3",
        "quantity": 120.5,
        "rate": 185.00,
        "amount": 22292.50,
        "trade": "concrete",
    }


def test_list_boq_amounts_are_quantity_times_rate(client):
    response = client.get(f"/projects/{PROJECT}/boq?per_page=100", headers=auth_headers())
    assert response.status_code == 200
    for item in response.json()["items"]:
        assert item["amount"] == round(item["quantity"] * item["rate"], 2)


def test_list_boq_pagination(client):
    page1 = client.get(f"/projects/{PROJECT}/boq?per_page=2", headers=auth_headers()).json()
    page2 = client.get(f"/projects/{PROJECT}/boq?per_page=2&page=2", headers=auth_headers()).json()
    assert [item["item_no"] for item in page1["items"]] == ["3.1", "3.2"]
    assert [item["item_no"] for item in page2["items"]] == ["3.3", "3.4"]
    assert page1["total_items"] == 37


def test_list_boq_trade_filter(client):
    response = client.get(f"/projects/{PROJECT}/boq?trade=concrete", headers=auth_headers())
    body = response.json()
    assert body["total_items"] == 19
    assert all(item["trade"] == "concrete" for item in body["items"])
    steel = client.get(f"/projects/{PROJECT}/boq?trade=steel", headers=auth_headers()).json()
    assert steel["total_items"] == 8


def test_get_boq_item_matches_reference(client):
    response = client.get(f"/projects/{PROJECT}/boq/3.1", headers=auth_headers())
    assert response.status_code == 200
    body = response.json()
    assert body["item_no"] == "3.1"
    assert body["quantity"] == 120.5
    assert body["amount"] == 22292.50
    assert body["updated_at"] == "2026-11-10T09:30:00+08:00"


def test_get_missing_item_returns_404(client):
    response = client.get(f"/projects/{PROJECT}/boq/9.9", headers=auth_headers())
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_unknown_project_returns_404(client):
    response = client.get("/projects/proj_NOPE/boq", headers=auth_headers())
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_summary_matches_reference(client):
    response = client.get(f"/projects/{PROJECT}/summary", headers=auth_headers())
    assert response.status_code == 200
    body = response.json()
    assert body["live_total"] == 1842500.00
    assert body["by_trade"] == [
        {"trade": "concrete", "total": 642300.00},
        {"trade": "finishes", "total": 681800.00},
        {"trade": "steel", "total": 518400.00},
    ]
    assert body["draft_estimate"] is None


def test_create_estimate_and_summary_shows_draft(client):
    payload = {
        "title": "November re-measure",
        "items": [
            {
                "description": "Grade 40 reinforced concrete, columns",
                "unit": "m3",
                "quantity": 120.5,
                "rate": 185.00,
            }
        ],
        "notes": "Re-measured from Revit model rev C.",
    }
    response = client.post(f"/projects/{PROJECT}/estimates", json=payload, headers=auth_headers())
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "draft"
    assert body["total_amount"] == 22292.50
    assert body["estimate_id"].startswith("est_")

    summary = client.get(f"/projects/{PROJECT}/summary", headers=auth_headers()).json()
    assert summary["draft_estimate"]["estimate_id"] == body["estimate_id"]
    assert summary["draft_estimate"]["total_amount"] == 22292.50
    assert summary["live_total"] == 1842500.00


def test_create_estimate_from_example_file(client):
    import json
    import pathlib

    payload = json.loads(pathlib.Path("examples/estimate.json").read_text())
    response = client.post(f"/projects/{PROJECT}/estimates", json=payload, headers=auth_headers())
    assert response.status_code == 201
    assert response.json()["total_amount"] == 22292.50


def test_create_estimate_invalid_quantity(client):
    payload = {
        "title": "Bad estimate",
        "items": [{"description": "Concrete", "unit": "m3", "quantity": 0, "rate": 185.00}],
    }
    response = client.post(f"/projects/{PROJECT}/estimates", json=payload, headers=auth_headers())
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "invalid_quantity"
    assert error["field"] == "items[0].quantity"


def test_create_estimate_invalid_rate(client):
    payload = {
        "title": "Bad estimate",
        "items": [{"description": "Concrete", "unit": "m3", "quantity": 10, "rate": -5}],
    }
    response = client.post(f"/projects/{PROJECT}/estimates", json=payload, headers=auth_headers())
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "invalid_rate"
    assert error["field"] == "items[0].rate"


def test_create_estimate_missing_title(client):
    payload = {
        "items": [{"description": "Concrete", "unit": "m3", "quantity": 10, "rate": 185.00}]
    }
    response = client.post(f"/projects/{PROJECT}/estimates", json=payload, headers=auth_headers())
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "missing_field"
    assert error["field"] == "title"


def test_missing_token_returns_401(client):
    response = client.get(f"/projects/{PROJECT}/boq")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_wrong_token_returns_401(client):
    response = client.get(f"/projects/{PROJECT}/boq", headers=auth_headers("not-the-token"))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_rate_limit_returns_429(client, monkeypatch):
    monkeypatch.setattr(main, "RATE_LIMIT", 3)
    token = "rate-test-token"
    monkeypatch.setattr(main, "API_TOKEN", token)
    main._hits.clear()
    for _ in range(3):
        response = client.get(f"/projects/{PROJECT}/boq", headers=auth_headers(token))
        assert response.status_code == 200
    response = client.get(f"/projects/{PROJECT}/boq", headers=auth_headers(token))
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limited"
    assert "Retry-After" in response.headers
