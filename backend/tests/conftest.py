"""Test fixtures for the Marea Alta backend test suite."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth
from app.database import get_db
from app.main import app
from app.models import Admin, Base
from app.routers.auth import reset_rate_limit
from app.routers.contact import reset_rate_limit as reset_contact_rate_limit
from app.routers.newsletter import reset_rate_limit as reset_newsletter_rate_limit
from app.routers.reservations import reset_rate_limit as reset_reservation_rate_limit
from app.routers.rsvps import reset_rate_limit as reset_rsvp_rate_limit
from app.seed import seed_blog, seed_menu, seed_schedule


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Keep the in-memory rate limiters from leaking between tests."""
    reset_rate_limit()
    reset_contact_rate_limit()
    reset_newsletter_rate_limit()
    reset_reservation_rate_limit()
    reset_rsvp_rate_limit()
    yield
    reset_rate_limit()
    reset_contact_rate_limit()
    reset_newsletter_rate_limit()
    reset_reservation_rate_limit()
    reset_rsvp_rate_limit()


@pytest.fixture()
def db_session():
    """Create an in-memory SQLite database with the default schedule and menu."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    seed_schedule(session)
    seed_menu(session)
    seed_blog(session)
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    """Create a test client with an in-memory SQLite database."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture()
def admin_user(db_session):
    """Create an admin user directly in the test database and return credentials."""
    username = "testadmin"
    password = "testpass123"
    admin = Admin(username=username, password_hash=auth.hash_password(password))
    db_session.add(admin)
    db_session.commit()
    return {"username": username, "password": password}


@pytest.fixture()
def auth_cookies(client, admin_user):
    """Login and set session cookies on the client."""
    resp = client.post(
        "/admin/login",
        data={
            "username": admin_user["username"],
            "password": admin_user["password"],
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    # resp.cookies works correctly with TestClient
    cookies_dict = dict(resp.cookies)
    session_token = cookies_dict.get("session_token")
    csrf_token = cookies_dict.get("csrf_token")
    if session_token:
        client.cookies.set("session_token", session_token)
    if csrf_token:
        client.cookies.set("csrf_token", csrf_token)
    return cookies_dict


@pytest.fixture()
def csrf_token(auth_cookies):
    """Extract the CSRF token from cookies."""
    return auth_cookies.get("csrf_token")
