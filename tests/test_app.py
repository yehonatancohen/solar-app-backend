import os
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

TEST_DB_URL = "sqlite+aiosqlite:///./test.db"
os.environ["DATABASE_URL"] = TEST_DB_URL

TEST_DB_PATH = Path("./test.db")
if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app  # noqa: E402
from app.calcs import solar  # noqa: E402


@pytest.fixture(scope="module")
def client():
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    with TestClient(app) as test_client:
        yield test_client
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


def create_auth_header(client: TestClient) -> dict[str, str]:
    email = f"user_{uuid4().hex}@example.com"
    password = "Passw0rd!"
    register_resp = client.post(
        "/auth/register",
        json={"name": "Tester", "email": email, "password": password},
    )
    assert register_resp.status_code == 200, register_resp.text
    login_resp = client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    assert login_resp.status_code == 200, login_resp.text
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_endpoint(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_register_duplicate_email(client: TestClient):
    email = f"dupe_{uuid4().hex}@example.com"
    payload = {"name": "Dupe", "email": email, "password": "Secret123"}
    first = client.post("/auth/register", json=payload)
    assert first.status_code == 200
    second = client.post("/auth/register", json=payload)
    assert second.status_code == 400
    assert second.json()["detail"] == "Email already registered"


def test_projects_require_auth(client: TestClient):
    resp = client.get("/projects")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Missing token"


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

    calc_resp = client.post(
        f"/projects/{project_id}/calculate", headers=headers
    )
    assert calc_resp.status_code == 200, calc_resp.text
    calculation = calc_resp.json()
    assert calculation["version"] == 1

    expected = solar.calculate(inputs_v2["payload_json"])
    assert calculation["results_json"] == expected
