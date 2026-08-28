import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.websockets import WebSocketDisconnect


@pytest.fixture
def client(tmp_path, monkeypatch):
    database_path = Path(tmp_path) / "syncus-test.db"
    database_url = f"sqlite:///{database_path}"
    test_secret = "test-secret-for-syncus-tests-32-chars"
    test_origins = "http://localhost:8080,http://127.0.0.1:8080"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("SECRET_KEY", test_secret)
    monkeypatch.setenv("CORS_ORIGINS", test_origins)
    monkeypatch.setenv("ALGORITHM", "HS256")

    # A fixture também atualiza o singleton caso outro módulo de teste tenha
    # importado `config` durante a coleta dos testes.
    from app.core import config

    config.settings.DATABASE_URL = database_url
    config.settings.ENVIRONMENT = "test"
    config.settings.SECRET_KEY = test_secret
    config.settings.CORS_ORIGINS = test_origins
    config.settings.ALGORITHM = "HS256"

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
    _register(client, "Alice", "alice@example.com")
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

    custom_payload = {
        "amount": 1000,
        "description": "Televisão",
        "category_id": category_id,
        "type": "saida",
        "date": "2026-08-11T12:00:00",
        "paid_by": "eu",
        "split_type": "custom",
        "custom_split_data": {"eu": 700, "parceira": 300},
    }
    custom = client.post(
        "/api/transactions/", headers=alice_headers, json=custom_payload
    )
    assert custom.status_code == 200, custom.text
    assert custom.json()["custom_split_data"] == '{"eu": "700.00", "parceira": "300.00"}'

    custom_dashboard = client.get(
        "/api/transactions/dashboard?year=2026&month=8", headers=bob_headers
    )
    assert custom_dashboard.status_code == 200
    assert custom_dashboard.json()["couple_balance"]["amount"] == 200

    invalid_custom = client.post(
        "/api/transactions/", headers=alice_headers,
        json={**custom_payload, "description": "Rateio inválido", "custom_split_data": {"eu": 800, "parceira": 300}},
    )
    assert invalid_custom.status_code == 400

    delete_all = client.delete("/api/transactions/all", headers=bob_headers)
    assert delete_all.status_code == 200, delete_all.text
    assert delete_all.json()["deleted"] == 1
    assert client.get("/api/transactions/", headers=alice_headers).json() == []



def _login_token(client, email):
    response = client.post(
        "/api/auth/login",
        data={"username": email, "password": "Senha123!"},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def test_websocket_manager_removes_dead_connections():
    from app.websockets.sync import ConnectionManager

    class HealthySocket:
        def __init__(self):
            self.messages = []

        async def send_json(self, message):
            self.messages.append(message)

    class DeadSocket:
        async def send_json(self, message):
            raise RuntimeError("socket encerrado")

    async def scenario():
        manager = ConnectionManager()
        healthy = HealthySocket()
        dead = DeadSocket()
        manager.active_connections[42] = [healthy, dead]

        await manager.broadcast({"type": "updated"}, 42)

        assert healthy.messages == [{"type": "updated"}]
        assert manager.active_connections[42] == [healthy]

    asyncio.run(scenario())


def test_websocket_rejects_missing_or_invalid_token(client):
    with pytest.raises(WebSocketDisconnect) as missing_token:
        with client.websocket_connect("/ws/"):
            pass
    assert missing_token.value.code == 1008

    with pytest.raises(WebSocketDisconnect) as invalid_token:
        with client.websocket_connect("/ws/?token=token-invalido"):
            pass
    assert invalid_token.value.code == 1008


def test_websocket_uses_authenticated_users_real_room(client):
    alice = _register(client, "Alice WS", "alice-ws@example.com")
    bob = _register(client, "Bob WS", "bob-ws@example.com")
    alice_token = _login_token(client, "alice-ws@example.com")
    bob_token = _login_token(client, "bob-ws@example.com")
    alice_headers = {"Authorization": f"Bearer {alice_token}"}
    bob_headers = {"Authorization": f"Bearer {bob_token}"}

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

    with client.websocket_connect(
        "/ws/", headers={"Authorization": f"Bearer {alice_token}"}
    ) as alice_socket:
        with client.websocket_connect(f"/ws/?token={bob_token}") as bob_socket:
            alice_socket.send_json({"type": "transaction.updated", "room_id": 999999})
            event = bob_socket.receive_json()

    assert event["type"] == "transaction.updated"
    assert event["room_id"] == alice_me["room_id"]
    assert event["room_id"] != 999999
    assert event["user_id"] == alice["id"]



def test_websocket_rejects_stale_room_without_active_connection(client):
    _register(client, "Stale room", "stale-room@example.com")
    token = _login_token(client, "stale-room@example.com")

    from app.core.database import SessionLocal
    from app.models.models import Room, User

    db = SessionLocal()
    try:
        room = Room()
        db.add(room)
        db.flush()
        db.query(User).filter(User.email == "stale-room@example.com").update(
            {User.room_id: room.id}, synchronize_session=False
        )
        db.commit()
    finally:
        db.close()

    with pytest.raises(WebSocketDisconnect) as stale_room:
        with client.websocket_connect(f"/ws/?token={token}"):
            pass
    assert stale_room.value.code == 1008



def test_active_connection_is_unique_per_user_and_conflicts_are_rejected(client):
    _register(client, "Alice occupied", "alice-occupied@example.com")
    bob = _register(client, "Bob occupied", "bob-occupied@example.com")
    carol = _register(client, "Carol occupied", "carol-occupied@example.com")
    alice_headers = _login(client, "alice-occupied@example.com")
    bob_headers = _login(client, "bob-occupied@example.com")
    carol_headers = _login(client, "carol-occupied@example.com")

    first_invite = client.post(
        "/api/couple/invite/send",
        headers=alice_headers,
        json={"token": bob["connection_token"]},
    )
    assert first_invite.status_code == 201, first_invite.text
    bob_notifications = client.get(
        "/api/couple/notifications", headers=bob_headers
    ).json()
    first_invite_id = bob_notifications[0]["related_id"]
    accepted = client.post(
        f"/api/couple/invite/{first_invite_id}/accept", headers=bob_headers
    )
    assert accepted.status_code == 200, accepted.text

    occupied_recipient = client.post(
        "/api/couple/invite/send",
        headers=carol_headers,
        json={"token": bob["connection_token"]},
    )
    assert occupied_recipient.status_code == 409
    assert "vínculo ativo" in occupied_recipient.json()["detail"]

    occupied_sender = client.post(
        "/api/couple/invite/send",
        headers=alice_headers,
        json={"token": carol["connection_token"]},
    )
    assert occupied_sender.status_code == 409
    assert "vínculo ativo" in occupied_sender.json()["detail"]

    disconnected = client.post("/api/couple/disconnect", headers=alice_headers)
    assert disconnected.status_code == 200, disconnected.text

    refreshed_alice = client.post(
        "/api/users/token/refresh", headers=alice_headers
    )
    assert refreshed_alice.status_code == 200, refreshed_alice.text

    reconnect = client.post(
        "/api/couple/invite/send",
        headers=carol_headers,
        json={"token": refreshed_alice.json()["connection_token"]},
    )
    assert reconnect.status_code == 201, reconnect.text


def test_database_rejects_two_active_connections_for_one_user():
    from app.core.database import Base
    from app.models.models import CoupleConnection, User

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        alice = User(
            name="Alice DB",
            email="alice-db@example.com",
            hashed_password="hash",
        )
        bob = User(
            name="Bob DB",
            email="bob-db@example.com",
            hashed_password="hash",
        )
        carol = User(
            name="Carol DB",
            email="carol-db@example.com",
            hashed_password="hash",
        )
        session.add_all([alice, bob, carol])
        session.commit()

        session.add(
            CoupleConnection(
                user1_id=alice.id,
                user2_id=bob.id,
                is_active=True,
            )
        )
        session.commit()

        session.add(
            CoupleConnection(
                user1_id=alice.id,
                user2_id=carol.id,
                is_active=True,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        session.add(
            CoupleConnection(
                user1_id=alice.id,
                user2_id=carol.id,
                is_active=False,
            )
        )
        session.commit()
    finally:
        session.close()
        engine.dispose()



def test_database_rejects_user_active_in_both_connection_positions():
    from app.core.database import Base
    from app.models.models import CoupleConnection, CoupleConnectionMember, User

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        users = [
            User(name="User 1", email="position-1@example.com", hashed_password="hash"),
            User(name="User 2", email="position-2@example.com", hashed_password="hash"),
            User(name="User 3", email="position-3@example.com", hashed_password="hash"),
        ]
        session.add_all(users)
        session.commit()

        first_connection = CoupleConnection(
            user1_id=users[0].id,
            user2_id=users[1].id,
            is_active=True,
        )
        second_connection = CoupleConnection(
            user1_id=users[1].id,
            user2_id=users[2].id,
            is_active=True,
        )
        session.add_all([first_connection, second_connection])
        session.flush()
        session.add_all(
            [
                CoupleConnectionMember(
                    connection_id=first_connection.id,
                    user_id=users[0].id,
                    is_active=True,
                ),
                CoupleConnectionMember(
                    connection_id=first_connection.id,
                    user_id=users[1].id,
                    is_active=True,
                ),
                CoupleConnectionMember(
                    connection_id=second_connection.id,
                    user_id=users[1].id,
                    is_active=True,
                ),
                CoupleConnectionMember(
                    connection_id=second_connection.id,
                    user_id=users[2].id,
                    is_active=True,
                ),
            ]
        )
        with pytest.raises(IntegrityError):
            session.commit()
    finally:
        session.close()
        engine.dispose()



def test_service_rejects_room_with_more_than_two_users():
    from app.core.database import Base
    from app.models.models import Room, User
    from app.services.room_service import ensure_room_for_users

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        room = Room()
        users = [
            User(name="Room User 1", email="room-1@example.com", hashed_password="hash"),
            User(name="Room User 2", email="room-2@example.com", hashed_password="hash"),
            User(name="Room User 3", email="room-3@example.com", hashed_password="hash"),
        ]
        session.add(room)
        session.flush()
        for user in users:
            user.room_id = room.id
        session.add_all(users)
        session.commit()

        with pytest.raises(ValueError, match="outros usuários"):
            ensure_room_for_users(session, users[0], users[2])
    finally:
        session.close()
        engine.dispose()



def test_startup_backfill_populates_connection_members_once():
    from app.core.database import Base
    from app.models.models import CoupleConnection, CoupleConnectionMember, User
    from app.services.room_service import ensure_active_connection_members

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        users = [
            User(name="Legacy 1", email="legacy-1@example.com", hashed_password="hash"),
            User(name="Legacy 2", email="legacy-2@example.com", hashed_password="hash"),
        ]
        session.add_all(users)
        session.commit()
        connection = CoupleConnection(
            user1_id=users[0].id,
            user2_id=users[1].id,
            is_active=True,
        )
        session.add(connection)
        session.commit()

        ensure_active_connection_members(session)
        ensure_active_connection_members(session)

        members = session.query(CoupleConnectionMember).all()
        assert len(members) == 2
        assert {member.user_id for member in members} == {users[0].id, users[1].id}
        assert all(member.is_active for member in members)
    finally:
        session.close()
        engine.dispose()



def test_cors_allows_only_configured_origins(client):
    allowed_origin = "http://localhost:8080"
    allowed = client.options(
        "/",
        headers={
            "Origin": allowed_origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == allowed_origin
    assert allowed.headers["access-control-allow-credentials"] == "true"

    denied = client.options(
        "/",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in denied.headers



def test_report_endpoint_returns_backend_aggregates(client):
    _register(client, "Report Alice", "report-alice@example.com")
    bob = _register(client, "Report Bob", "report-bob@example.com")
    alice_headers = _login(client, "report-alice@example.com")
    bob_headers = _login(client, "report-bob@example.com")

    invite = client.post(
        "/api/couple/invite/send",
        headers=alice_headers,
        json={"token": bob["connection_token"]},
    )
    assert invite.status_code == 201, invite.text
    notification = client.get(
        "/api/couple/notifications", headers=bob_headers
    ).json()[0]
    accepted = client.post(
        f"/api/couple/invite/{notification['related_id']}/accept",
        headers=bob_headers,
    )
    assert accepted.status_code == 200, accepted.text

    categories = client.get(
        "/api/transactions/categories", headers=alice_headers
    ).json()
    category_id = categories[0]["id"]
    for payload in (
        {
            "amount": "0.10",
            "description": "Pequena compra",
            "category_id": category_id,
            "type": "saida",
            "date": "2026-08-27T12:00:00",
            "paid_by": "eu",
            "split_type": "50/50",
        },
        {
            "amount": "0.20",
            "description": "Outra compra",
            "category_id": category_id,
            "type": "saida",
            "date": "2026-08-27T12:00:00",
            "paid_by": "parceira",
            "split_type": "100_user2",
        },
    ):
        response = client.post(
            "/api/transactions/", headers=alice_headers, json=payload
        )
        assert response.status_code == 200, response.text

    report = client.get(
        "/api/transactions/report?year=2026&month=8&payer=ambos",
        headers=alice_headers,
    )
    assert report.status_code == 200, report.text
    data = report.json()
    assert data["aggregates"]["transaction_count"] == 2
    assert data["aggregates"]["daily"]["2026-08-27"]["saida"] == "0.30"
    assert data["aggregates"]["payer_totals"]["eu"] == "0.10"
    assert data["aggregates"]["payer_totals"]["parceira"] == "0.20"
    assert data["transactions"][0]["amount"] == "0.10"


def test_gender_is_saved_and_exposed_for_partner(client):
    alice = client.post(
        "/api/auth/register",
        json={
            "name": "Alice Gender",
            "email": "alice-gender@example.com",
            "gender": "mulher",
            "password": "Senha123!",
        },
    )
    bob = client.post(
        "/api/auth/register",
        json={
            "name": "Bob Gender",
            "email": "bob-gender@example.com",
            "gender": "homem",
            "password": "Senha123!",
        },
    )
    assert alice.status_code == 200, alice.text
    assert bob.status_code == 200, bob.text

    alice_headers = _login(client, "alice-gender@example.com")
    bob_headers = _login(client, "bob-gender@example.com")
    alice_me = client.get("/api/users/me", headers=alice_headers)
    assert alice_me.status_code == 200
    assert alice_me.json()["gender"] == "mulher"

    invite = client.post(
        "/api/couple/invite/send",
        headers=alice_headers,
        json={"token": bob.json()["connection_token"]},
    )
    assert invite.status_code == 201, invite.text
    notification = client.get(
        "/api/couple/notifications", headers=bob_headers
    ).json()[0]
    assert "sua parceira" in notification["message"]
    accepted = client.post(
        f"/api/couple/invite/{notification['related_id']}/accept",
        headers=bob_headers,
    )
    assert accepted.status_code == 200, accepted.text

    partner = client.get("/api/couple/partner", headers=alice_headers)
    assert partner.status_code == 200, partner.text
    assert partner.json()["parceiro"]["gender"] == "homem"


def test_user_can_delete_one_notification_and_clear_read_notifications(client):
    _register(client, "Alice Notifications", "alice-notifications@example.com")
    bob = _register(client, "Bob Notifications", "bob-notifications@example.com")
    alice_headers = _login(client, "alice-notifications@example.com")
    bob_headers = _login(client, "bob-notifications@example.com")

    first_invite = client.post(
        "/api/couple/invite/send",
        headers=alice_headers,
        json={"token": bob["connection_token"]},
    )
    assert first_invite.status_code == 201, first_invite.text
    first_notifications = client.get(
        "/api/couple/notifications", headers=bob_headers
    ).json()
    assert len(first_notifications) == 1

    marked = client.put(
        "/api/couple/notifications/read-all", headers=bob_headers
    )
    assert marked.status_code == 200, marked.text
    cleared = client.delete(
        "/api/couple/notifications/clear/read", headers=bob_headers
    )
    assert cleared.status_code == 200, cleared.text
    assert client.get(
        "/api/couple/notifications", headers=bob_headers
    ).json() == []

    second_invite = client.post(
        "/api/couple/invite/send",
        headers=alice_headers,
        json={"token": bob["connection_token"]},
    )
    assert second_invite.status_code == 201, second_invite.text
    second_notification = client.get(
        "/api/couple/notifications", headers=bob_headers
    ).json()[0]
    deleted = client.delete(
        f"/api/couple/notifications/{second_notification['id']}",
        headers=bob_headers,
    )
    assert deleted.status_code == 200, deleted.text
    assert client.get(
        "/api/couple/notifications", headers=bob_headers
    ).json() == []

    # A notificação já foi apagada; outro usuário não recebe acesso ao recurso.
    forbidden_delete = client.delete(
        f"/api/couple/notifications/{second_notification['id']}",
        headers=alice_headers,
    )
    assert forbidden_delete.status_code == 404
