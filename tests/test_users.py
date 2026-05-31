from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db.dependencies import get_db
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
        user_id = self._selected_user_id(statement)

        if user_id is None:
            return FakeResult(self.users)

        return FakeResult(
            [user for user in self.users if user.id == user_id]
        )

    async def delete(self, user):
        self.deleted_users.append(user)
        self.users.remove(user)

    def _selected_user_id(self, statement):
        whereclause = getattr(statement, "whereclause", None)

        if whereclause is None:
            return None

        right_side = getattr(whereclause, "right", None)

        return getattr(right_side, "value", None)


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
    fake_db = use_fake_db(FakeAsyncSession())

    response = await client.post(
        "/users",
        json={"name": "TestUser"}
    )

    assert response.status_code == 200

    data = response.json()

    assert data == {"id": 1, "name": "TestUser"}
    assert fake_db.commits == 1
    assert [user.name for user in fake_db.users] == ["TestUser"]
    mock_send_notification.assert_awaited_once_with(
        "New user created: TestUser"
    )


@pytest.mark.asyncio
async def test_get_users(client, use_fake_db):
    use_fake_db(
        FakeAsyncSession(
            [
                User(id=1, name="Ada"),
                User(id=2, name="Grace")
            ]
        )
    )

    response = await client.get("/users")

    assert response.status_code == 200
    assert response.json() == [
        {"id": 1, "name": "Ada"},
        {"id": 2, "name": "Grace"}
    ]


@pytest.mark.asyncio
async def test_update_user(client, use_fake_db):
    fake_db = use_fake_db(
        FakeAsyncSession([User(id=1, name="OldName")])
    )

    response = await client.put(
        "/users/1",
        json={"name": "NewName"}
    )

    assert response.status_code == 200
    assert response.json() == {"id": 1, "name": "NewName"}
    assert fake_db.users[0].name == "NewName"
    assert fake_db.commits == 1


@pytest.mark.asyncio
async def test_update_user_returns_404_when_missing(client, use_fake_db):
    fake_db = use_fake_db(FakeAsyncSession())

    response = await client.put(
        "/users/404",
        json={"name": "Nobody"}
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}
    assert fake_db.commits == 0


@pytest.mark.asyncio
async def test_delete_user(client, use_fake_db):
    user = User(id=1, name="DeleteMe")
    fake_db = use_fake_db(FakeAsyncSession([user]))

    response = await client.delete("/users/1")

    assert response.status_code == 200
    assert response.json() == {"message": "User deleted"}
    assert fake_db.users == []
    assert fake_db.deleted_users == [user]
    assert fake_db.commits == 1


@pytest.mark.asyncio
async def test_delete_user_returns_404_when_missing(client, use_fake_db):
    fake_db = use_fake_db(FakeAsyncSession())

    response = await client.delete("/users/404")

    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}
    assert fake_db.deleted_users == []
    assert fake_db.commits == 0
