import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    database_path = Path(tmp_path) / "syncus-test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("ALGORITHM", "HS256")

    # O app é importado após as variáveis para que a sessão use o banco temporário.
    from app.main import app

    return TestClient(app)


def _register(client, name, email):
    response = client.post(
        "/api/auth/register",
        json={"name": name, "email": email, "password": "Senha123!"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _login(client, email):
    response = client.post(
        "/api/auth/login",
        data={"username": email, "password": "Senha123!"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_auth_link_and_financial_crud(client):
    alice = _register(client, "Alice", "alice@example.com")
    bob = _register(client, "Bob", "bob@example.com")
    alice_headers = _login(client, "alice@example.com")
    bob_headers = _login(client, "bob@example.com")

    invite = client.post(
        "/api/couple/invite/send",
        headers=alice_headers,
        json={"token": bob["connection_token"]},
    )
    assert invite.status_code == 201, invite.text

    notifications = client.get("/api/couple/notifications", headers=bob_headers)
    assert notifications.status_code == 200
    invite_id = notifications.json()[0]["related_id"]

    accepted = client.post(
        f"/api/couple/invite/{invite_id}/accept", headers=bob_headers
    )
    assert accepted.status_code == 200, accepted.text

    alice_me = client.get("/api/users/me", headers=alice_headers).json()
    bob_me = client.get("/api/users/me", headers=bob_headers).json()
    assert alice_me["room_id"] == bob_me["room_id"]

    categories = client.get("/api/transactions/categories", headers=alice_headers)
    assert categories.status_code == 200
    category_id = categories.json()[0]["id"]

    payload = {
        "amount": 100,
        "description": "Mercado",
        "category_id": category_id,
        "type": "saida",
        "date": "2026-08-10T12:00:00",
        "paid_by": "eu",
        "split_type": "50/50",
        "custom_split_data": None,
    }
    created = client.post("/api/transactions/", headers=alice_headers, json=payload)
    assert created.status_code == 200, created.text
    transaction_id = created.json()["id"]

    listed = client.get("/api/transactions/?type=saida&limit=500", headers=bob_headers)
    assert listed.status_code == 200
    assert listed.json()[0]["description"] == "Mercado"

    updated = client.put(
        f"/api/transactions/{transaction_id}",
        headers=bob_headers,
        json={"amount": 120},
    )
    assert updated.status_code == 200
    assert updated.json()["amount"] == 120

    dashboard = client.get(
        "/api/transactions/dashboard?year=2026&month=8", headers=alice_headers
    )
    assert dashboard.status_code == 200
    assert dashboard.json()["summary"]["monthly_expenses"] == 120
    assert dashboard.json()["couple_balance"]["amount"] == 60
    assert len(dashboard.json()["chart_data"]["labels"]) == 31

    filtered = client.get(
        "/api/transactions/?start_date=2026-08-01T00:00:00&end_date=2026-09-01T00:00:00&limit=500",
        headers=alice_headers,
    )
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1

    deleted = client.delete(
        f"/api/transactions/{transaction_id}", headers=bob_headers
    )
    assert deleted.status_code == 200
    assert client.get("/api/transactions/", headers=alice_headers).json() == []
