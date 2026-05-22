import os
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-minimum-32-chars-ok!")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
# Bypass per-IP rate limits in unit tests (the same flag is honoured in prod
# only via DEBUG=true, which validate_secret_key still requires a real key for).
os.environ.setdefault("DEBUG", "true")
# Force the Whisper service into mock mode for offline-safe tests.
os.environ["MOCK_WHISPER"] = "true"
import types
import bcrypt as _bcrypt
if not hasattr(_bcrypt, '__about__'):
    _bcrypt.__about__ = types.SimpleNamespace(__version__=_bcrypt.__version__)

import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.database import Base, get_db
from app.main import app
from app.auth import hash_password, create_access_token
from app.models.user import User, UserRole
from app import models as _models  # ensure all models are registered in Base.metadata

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(TEST_DB_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine):
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(engine):
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def override_get_db():
        async with async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def broker_user(db_session: AsyncSession):
    unique = uuid.uuid4().hex[:8]
    user = User(
        email=f"broker_{unique}@example.com",
        hashed_password=hash_password("password123"),
        full_name="Test Broker",
        role=UserRole.CUSTOMS_BROKER,
        company_id=uuid.uuid4(),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def compliance_user(db_session: AsyncSession):
    unique = uuid.uuid4().hex[:8]
    user = User(
        email=f"compliance_{unique}@example.com",
        hashed_password=hash_password("password123"),
        full_name="Compliance Officer",
        role=UserRole.TRADE_COMPLIANCE,
        company_id=uuid.uuid4(),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def broker_token(broker_user):
    return create_access_token(str(broker_user.id))


@pytest.fixture
def compliance_token(compliance_user):
    return create_access_token(str(compliance_user.id))


@pytest_asyncio.fixture
async def auth_client(engine):
    """Authenticated AsyncClient with a fresh user per test."""
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def override_get_db():
        async with async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        unique = uuid.uuid4().hex[:8]
        email = f"test_{unique}@example.com"
        reg = await c.post("/api/v1/auth/register", json={
            "email": email, "password": "TestPass1!", "full_name": "Test User",
            "role": "customs_broker",
        })
        assert reg.status_code == 201, f"Registration failed: {reg.text}"
        login = await c.post(
            "/api/v1/auth/login",
            data={"username": email, "password": "TestPass1!"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert login.status_code == 200, f"Login failed: {login.text}"
        token = login.json()["access_token"]
        c.headers.update({"Authorization": f"Bearer {token}"})
        yield c
    app.dependency_overrides.clear()
