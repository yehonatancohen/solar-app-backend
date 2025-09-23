import hashlib
import hmac
import json
import os
import sys
import time
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

TEST_DB_URL = "sqlite+aiosqlite:///./test.db"
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["STRIPE_SECRET_KEY"] = "sk_test_123"
os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_test"
os.environ["FRONTEND_DOMAIN"] = "https://frontend.test"

TEST_DB_PATH = Path("./test.db")
if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app  # noqa: E402
from app.calcs import solar  # noqa: E402


@pytest.fixture(autouse=True)
def mock_stripe_checkout(monkeypatch):
    from app.routers import payments as payments_router

    def _create(cls, **kwargs):
        return {
            "id": f"cs_test_{uuid4().hex}",
            "url": "https://checkout.stripe.com/pay/test-session",
            "mode": "payment",
        }

    monkeypatch.setattr(
        payments_router.stripe.checkout.Session,
        "create",
        classmethod(_create),
    )
    yield


@pytest.fixture(scope="module")
def client():
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    with TestClient(app) as test_client:
        yield test_client
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


def trigger_stripe_completion(client: TestClient, *, user_id: int, session_id: str) -> None:
    event = {
        "id": f"evt_{uuid4().hex}",
        "object": "event",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": session_id,
                "metadata": {"user_id": str(user_id)},
            }
        },
    }
    payload = json.dumps(event)
    timestamp = int(time.time())
    secret = os.environ["STRIPE_WEBHOOK_SECRET"].encode()
    signature = hmac.new(
        secret, f"{timestamp}.{payload}".encode(), hashlib.sha256
    ).hexdigest()
    header = f"t={timestamp},v1={signature}"
    resp = client.post(
        "/payments/webhook/stripe",
        data=payload,
        headers={
            "Stripe-Signature": header,
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 200, resp.text


def create_auth_header(
    client: TestClient,
    *,
    payment: dict | None = None,
    activate: bool = True,
) -> dict[str, str]:
    email = f"user_{uuid4().hex}@example.com"
    password = "Passw0rd!"
    payment_payload = payment or {
        "method": "visa",
        "card_number": "4242424242424242",
    }
    register_resp = client.post(
        "/auth/register",
        json={
            "name": "Tester",
            "email": email,
            "password": password,
            "payment": payment_payload,
        },
    )
    assert register_resp.status_code == 200, register_resp.text
    user_data = register_resp.json()
    assert user_data["is_active"] is False
    login_resp = client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    assert login_resp.status_code == 200, login_resp.text
    login_data = login_resp.json()
    assert login_data["is_active"] is False
    token = login_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    if activate:
        checkout_resp = client.post(
            "/payments/checkout",
            json={"provider": "stripe"},
            headers=headers,
        )
        assert checkout_resp.status_code == 200, checkout_resp.text
        session_id = checkout_resp.json()["session_id"]
        trigger_stripe_completion(
            client, user_id=user_data["id"], session_id=session_id
        )
        me_resp = client.get("/auth/me", headers=headers)
        assert me_resp.status_code == 200
        assert me_resp.json()["is_active"] is True
    return headers


def test_health_endpoint(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_register_duplicate_email(client: TestClient):
    email = f"dupe_{uuid4().hex}@example.com"
    payload = {
        "name": "Dupe",
        "email": email,
        "password": "Secret123",
        "payment": {"method": "visa", "card_number": "4111111111111111"},
    }
    first = client.post("/auth/register", json=payload)
    assert first.status_code == 200
    second = client.post("/auth/register", json=payload)
    assert second.status_code == 400
    assert second.json()["detail"] == "Email already registered"


def test_projects_require_auth(client: TestClient):
    resp = client.get("/projects")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Missing token"


def test_inactive_user_needs_payment(client: TestClient):
    headers = create_auth_header(client, activate=False)
    resp = client.get("/projects", headers=headers)
    assert resp.status_code == 402
    assert resp.json()["detail"] == "Payment required"


def test_project_flow_with_calculation(client: TestClient):
    headers = create_auth_header(client)
    project_payload = {
        "name": "Solar Roof",
        "site_location_json": {"lat": 10.0, "lon": -20.0},
        "currency": "USD",
    }
    create_resp = client.post("/projects", json=project_payload, headers=headers)
    assert create_resp.status_code == 200, create_resp.text
    project = create_resp.json()
    assert project["name"] == project_payload["name"]
    project_id = project["id"]

    list_resp = client.get("/projects", headers=headers)
    assert list_resp.status_code == 200
    projects = list_resp.json()
    assert any(p["id"] == project_id for p in projects)

    inputs_v1 = {
        "payload_json": {
            "pv": {"panel_watts": 500, "num_panels": 8, "losses_pct": 12},
            "inverter": {"efficiency_pct": 97},
        }
    }
    inputs_resp = client.post(
        f"/projects/{project_id}/inputs", json=inputs_v1, headers=headers
    )
    assert inputs_resp.status_code == 200, inputs_resp.text
    saved_inputs = inputs_resp.json()
    assert saved_inputs["version"] == 1

    inputs_v2 = {
        "payload_json": {
            "pv": {"panel_watts": 540, "num_panels": 10, "losses_pct": 10},
            "inverter": {"efficiency_pct": 96},
        }
    }
    inputs_resp_v2 = client.post(
        f"/projects/{project_id}/inputs", json=inputs_v2, headers=headers
    )
    assert inputs_resp_v2.status_code == 200, inputs_resp_v2.text
    saved_inputs_v2 = inputs_resp_v2.json()
    assert saved_inputs_v2["version"] == 2

    calc_resp = client.post(f"/projects/{project_id}/calculate", headers=headers)
    assert calc_resp.status_code == 200, calc_resp.text
    calculation = calc_resp.json()
    assert calculation["version"] == 1

    expected = solar.calculate(inputs_v2["payload_json"])
    assert calculation["results_json"] == expected

    viz_payload = {
        "chart_type": "generation_curve",
        "config_json": {"series": [1, 2, 3], "labels": ["M", "T", "W"]},
    }
    viz_resp = client.post(
        f"/projects/{project_id}/visualizations",
        json=viz_payload,
        headers=headers,
    )
    assert viz_resp.status_code == 200, viz_resp.text
    visualization = viz_resp.json()
    assert visualization["chart_type"] == "generation_curve"

    viz_list = client.get(
        f"/projects/{project_id}/visualizations", headers=headers
    )
    assert viz_list.status_code == 200
    assert any(v["id"] == visualization["id"] for v in viz_list.json())

    report_payload = {
        "format": "pdf",
        "deliver_to": {"email": "owner@example.com", "whatsapp": "+15551234"},
    }
    report_resp = client.post(
        f"/projects/{project_id}/reports", json=report_payload, headers=headers
    )
    assert report_resp.status_code == 200, report_resp.text
    report = report_resp.json()
    assert report["format"] == "pdf"
    assert report["deliver_to_json"]["email"] == "owner@example.com"

    reports_list = client.get(
        f"/projects/{project_id}/reports", headers=headers
    )
    assert reports_list.status_code == 200
    assert any(r["id"] == report["id"] for r in reports_list.json())

    payment_resp = client.get("/payments/me", headers=headers)
    assert payment_resp.status_code == 200
    payment = payment_resp.json()
    assert payment["method_type"] == "visa"
    assert payment["details_json"]["last4"] == "4242"

    social_resp = client.post(
        "/users/me/social-links",
        json={"platform": "linkedin", "handle": "solar-pro"},
        headers=headers,
    )
    assert social_resp.status_code == 200, social_resp.text
    social_links = client.get("/users/me/social-links", headers=headers)
    assert social_links.status_code == 200
    assert any(link["platform"] == "linkedin" for link in social_links.json())

    dash_resp = client.post(
        "/users/me/dashboards",
        json={
            "name": "Installer View",
            "preference": "installer",
            "layout_json": {"widgets": ["summary", "alerts"]},
        },
        headers=headers,
    )
    assert dash_resp.status_code == 200, dash_resp.text

    dash_resp2 = client.post(
        "/users/me/dashboards",
        json={
            "name": "Analyst View",
            "preference": "analyst",
            "layout_json": {"widgets": ["charts"]},
        },
        headers=headers,
    )
    assert dash_resp2.status_code == 200, dash_resp2.text

    dashboards = client.get(
        "/users/me/dashboards", headers=headers, params={"preference": "installer"}
    )
    assert dashboards.status_code == 200
    data = dashboards.json()
    assert len(data) == 1
    assert data[0]["preference"] == "installer"

    notif_resp = client.post(
        "/notifications",
        json={
            "title": "Maintenance Reminder",
            "message": "Inspect panels in 7 days.",
            "delivery_channel": "push",
            "schedule_json": {"days": 7},
        },
        headers=headers,
    )
    assert notif_resp.status_code == 200, notif_resp.text
    notifications = client.get("/notifications", headers=headers)
    assert notifications.status_code == 200
    assert any(n["title"] == "Maintenance Reminder" for n in notifications.json())


def test_payment_mobile_money_option(client: TestClient):
    headers = create_auth_header(
        client,
        payment={"method": "mobile_money", "phone_number": "+250700000001"},
    )
    payment_resp = client.get("/payments/me", headers=headers)
    assert payment_resp.status_code == 200
    payment = payment_resp.json()
    assert payment["method_type"] == "mobile_money"
    assert payment["details_json"]["phone_number"] == "+250700000001"
