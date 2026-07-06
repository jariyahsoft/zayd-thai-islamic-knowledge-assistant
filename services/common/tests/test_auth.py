import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from zayd_common.auth import AuthError, AuthService, hash_password, verify_password
from zayd_common.database.models import AuditLog, AuthSession, Base
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork


@pytest.fixture
def auth_service() -> AuthService:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    return AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")


def test_password_hash_uses_adaptive_pbkdf2() -> None:
    encoded = hash_password("very-strong-password")
    assert encoded.startswith("pbkdf2_sha256$310000$")
    assert verify_password("very-strong-password", encoded)
    assert not verify_password("wrong-password", encoded)


def test_register_login_refresh_reuse_revokes_session(auth_service: AuthService) -> None:
    registered = auth_service.register(
        email="Person@Example.com",
        password="very-strong-password",
        display_name="Person",
    )
    assert registered.user.email == "person@example.com"

    logged_in = auth_service.login(
        email="person@example.com",
        password="very-strong-password",
    )
    rotated = auth_service.refresh(refresh_token=logged_in.tokens.refresh_token)
    assert rotated.refresh_token != logged_in.tokens.refresh_token

    with pytest.raises(AuthError) as exc_info:
        auth_service.refresh(refresh_token=logged_in.tokens.refresh_token)

    assert exc_info.value.code == "AUTH_REFRESH_REUSE_DETECTED"
    with auth_service.uow:
        session = auth_service.uow.session
        assert session is not None
        auth_sessions = session.execute(select(AuthSession)).scalars().all()
        assert any(auth_session.revoked_at is not None for auth_session in auth_sessions)


def test_login_rate_limit_and_audit_without_secrets(auth_service: AuthService) -> None:
    auth_service.register(
        email="rate@example.com",
        password="very-strong-password",
        display_name="Rate",
    )

    for _ in range(5):
        with pytest.raises(AuthError):
            auth_service.login(email="rate@example.com", password="wrong-password")

    with pytest.raises(AuthError) as exc_info:
        auth_service.login(email="rate@example.com", password="wrong-password")

    assert exc_info.value.code == "AUTH_RATE_LIMITED"
    with auth_service.uow:
        session = auth_service.uow.session
        assert session is not None
        logs = session.execute(select(AuditLog)).scalars().all()
        serialized = " ".join(
            f"{log.action} {log.reason or ''} {log.before_summary or ''} {log.after_summary or ''}"
            for log in logs
        )
        assert "wrong-password" not in serialized
        assert "very-strong-password" not in serialized


def test_password_reset_revokes_sessions(auth_service: AuthService) -> None:
    auth_service.register(
        email="reset@example.com",
        password="very-strong-password",
        display_name="Reset",
    )
    logged_in = auth_service.login(email="reset@example.com", password="very-strong-password")
    reset_token = auth_service.request_password_reset(email="reset@example.com")
    assert reset_token is not None

    auth_service.reset_password(reset_token=reset_token, new_password="new-strong-password")

    with pytest.raises(AuthError):
        auth_service.refresh(refresh_token=logged_in.tokens.refresh_token)

    logged_in_again = auth_service.login(email="reset@example.com", password="new-strong-password")
    assert logged_in_again.tokens.access_token


def test_revoke_all_sessions(auth_service: AuthService) -> None:
    result = auth_service.register(
        email="revoke@example.com",
        password="very-strong-password",
        display_name="Revoke",
    )
    auth_service.login(email="revoke@example.com", password="very-strong-password")
    revoked = auth_service.revoke_all_sessions(user_id=result.user.id)

    assert revoked == 2
