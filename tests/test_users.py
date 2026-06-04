from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db.dependencies import get_db
from app.auth.jwt_handler import create_access_token
from app.auth.security import hash_password
from app.main import app
from app.models.user import User
from app.routers import users as users_router


class FakeResult:
    def __init__(self, users):
        self.users = users

    def scalars(self):
        return self

    def all(self):
        return self.users

    def scalar_one_or_none(self):
        return self.users[0] if self.users else None


class FakeAsyncSession:
    def __init__(self, users=None):
        self.users = users or []
        self.commits = 0
        self.deleted_users = []
        self.next_id = max([user.id for user in self.users], default=0) + 1

    def add(self, user):
        user.id = self.next_id
        self.next_id += 1
        self.users.append(user)

    async def commit(self):
        self.commits += 1

    async def refresh(self, user):
        return user

    async def execute(self, statement):
        selected_filter = self._selected_filter(statement)

        if selected_filter is None:
            return FakeResult(self.users)

        key, value = selected_filter

        return FakeResult([
            user for user in self.users
            if getattr(user, key) == value
        ])

    async def delete(self, user):
        self.deleted_users.append(user)
        self.users.remove(user)

    def _selected_filter(self, statement):
        whereclause = getattr(statement, "whereclause", None)

        if whereclause is None:
            return None

        left_side = getattr(whereclause, "left", None)
        right_side = getattr(whereclause, "right", None)

        return (
            getattr(left_side, "key", None),
            getattr(right_side, "value", None)
        )


def make_user(
    user_id=1,
    name="TestUser",
    username="testuser",
    password_hash="hashed-password",
    role="user"
):
    return User(
        id=user_id,
        name=name,
        username=username,
        password_hash=password_hash,
        role=role
    )


def auth_headers(user):
    token = create_access_token(
        {
            "sub": str(user.id),
            "username": user.username,
            "role": user.role
        }
    )

    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test"
    ) as async_client:
        yield async_client


@pytest.fixture
def use_fake_db():
    def override_with(fake_db):
        async def override_get_db():
            yield fake_db

        app.dependency_overrides[get_db] = override_get_db

        return fake_db

    yield override_with

    app.dependency_overrides.clear()


@pytest.fixture
def mock_send_notification(monkeypatch):
    mock = AsyncMock()

    monkeypatch.setattr(users_router, "send_notification", mock)

    return mock


@pytest.mark.asyncio
async def test_create_user(client, use_fake_db, mock_send_notification):
    admin = make_user(
        user_id=1,
        name="Admin",
        username="admin",
        role="admin"
    )
    fake_db = use_fake_db(FakeAsyncSession([admin]))

    response = await client.post(
        "/users",
        json={
            "name": "TestUser",
            "username": "testuser",
            "password": "secret",
            "role": "user"
        },
        headers=auth_headers(admin)
    )

    assert response.status_code == 200

    data = response.json()

    assert data == {
        "id": 2,
        "name": "TestUser",
        "username": "testuser",
        "role": "user"
    }
    assert fake_db.commits == 1
    assert [user.name for user in fake_db.users] == ["Admin", "TestUser"]
    assert fake_db.users[1].password_hash != "secret"
    mock_send_notification.assert_awaited_once_with(
        "New user created: TestUser"
    )


@pytest.mark.asyncio
async def test_get_users(client, use_fake_db):
    admin = make_user(
        user_id=1,
        name="Admin",
        username="admin",
        role="admin"
    )
    use_fake_db(
        FakeAsyncSession(
            [
                admin,
                make_user(user_id=2, name="Ada", username="ada"),
                make_user(user_id=3, name="Grace", username="grace")
            ]
        )
    )

    response = await client.get(
        "/users",
        headers=auth_headers(admin)
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "name": "Admin",
            "username": "admin",
            "role": "admin"
        },
        {
            "id": 2,
            "name": "Ada",
            "username": "ada",
            "role": "user"
        },
        {
            "id": 3,
            "name": "Grace",
            "username": "grace",
            "role": "user"
        }
    ]


@pytest.mark.asyncio
async def test_update_user(client, use_fake_db):
    user = make_user(user_id=1, name="OldName")
    fake_db = use_fake_db(
        FakeAsyncSession([user])
    )

    response = await client.put(
        "/users/1",
        json={"name": "NewName"},
        headers=auth_headers(user)
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "name": "NewName",
        "username": "testuser",
        "role": "user"
    }
    assert fake_db.users[0].name == "NewName"
    assert fake_db.commits == 1


@pytest.mark.asyncio
async def test_update_user_returns_404_when_missing(client, use_fake_db):
    admin = make_user(
        user_id=1,
        name="Admin",
        username="admin",
        role="admin"
    )
    fake_db = use_fake_db(FakeAsyncSession([admin]))

    response = await client.put(
        "/users/404",
        json={"name": "Nobody"},
        headers=auth_headers(admin)
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}
    assert fake_db.commits == 0


@pytest.mark.asyncio
async def test_delete_user(client, use_fake_db):
    admin = make_user(
        user_id=1,
        name="Admin",
        username="admin",
        role="admin"
    )
    user = make_user(user_id=2, name="DeleteMe", username="deleteme")
    fake_db = use_fake_db(FakeAsyncSession([admin, user]))

    response = await client.delete(
        "/users/2",
        headers=auth_headers(admin)
    )

    assert response.status_code == 200
    assert response.json() == {"message": "User deleted"}
    assert fake_db.users == [admin]
    assert fake_db.deleted_users == [user]
    assert fake_db.commits == 1


@pytest.mark.asyncio
async def test_delete_user_returns_404_when_missing(client, use_fake_db):
    admin = make_user(
        user_id=1,
        name="Admin",
        username="admin",
        role="admin"
    )
    fake_db = use_fake_db(FakeAsyncSession([admin]))

    response = await client.delete(
        "/users/404",
        headers=auth_headers(admin)
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}
    assert fake_db.deleted_users == []
    assert fake_db.commits == 0


@pytest.mark.asyncio
async def test_users_require_authentication(client, use_fake_db):
    use_fake_db(FakeAsyncSession())

    response = await client.get("/users")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_register_user_hashes_password(client, use_fake_db):
    fake_db = use_fake_db(FakeAsyncSession())

    response = await client.post(
        "/register",
        json={
            "name": "New User",
            "username": "newuser",
            "password": "secret"
        }
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "name": "New User",
        "username": "newuser",
        "role": "user"
    }
    assert fake_db.users[0].password_hash != "secret"
    assert fake_db.commits == 1


@pytest.mark.asyncio
async def test_login_returns_access_token(client, use_fake_db):
    user = make_user(
        user_id=1,
        password_hash=hash_password("secret")
    )
    use_fake_db(FakeAsyncSession([user]))

    response = await client.post(
        "/login",
        data={
            "username": "testuser",
            "password": "secret"
        }
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


@pytest.mark.asyncio
async def test_me_returns_current_user(client, use_fake_db):
    user = make_user(user_id=1)
    use_fake_db(FakeAsyncSession([user]))

    response = await client.get(
        "/me",
        headers=auth_headers(user)
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "name": "TestUser",
        "username": "testuser",
        "role": "user"
    }


@pytest.mark.asyncio
async def test_non_admin_cannot_delete_user(client, use_fake_db):
    user = make_user(user_id=1)
    use_fake_db(FakeAsyncSession([user]))

    response = await client.delete(
        "/users/1",
        headers=auth_headers(user)
    )

    assert response.status_code == 403
