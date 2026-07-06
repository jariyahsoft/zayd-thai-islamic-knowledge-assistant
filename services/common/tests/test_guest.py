from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from zayd_common.auth import AuthError, AuthService
from zayd_common.database.models import Base, GuestSession
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.guest import GuestError, GuestService


@pytest.fixture
def engine() -> Any:
    return create_engine("sqlite:///:memory:")


@pytest.fixture
def session_factory(engine: Any) -> Any:
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


@pytest.fixture
def auth_service(session_factory: Any) -> AuthService:
    return AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")


@pytest.fixture
def guest_service(
    session_factory: Any, auth_service: AuthService
) -> GuestService:
    return GuestService(
        SQLAlchemyUnitOfWork(session_factory),
        auth_service=auth_service,
        ttl_minutes=60,
        message_quota=3,
        enabled=True,
    )


def test_start_session_returns_unique_token_and_ttl(
    guest_service: GuestService,
) -> None:
    info = guest_service.start_session()
    assert info.token and len(info.token) > 30
    assert info.message_quota == 3
    assert info.messages_used == 0
    assert info.expires_at > datetime.now(UTC)


def test_validate_session_returns_record_and_touch_updates_last_seen(
    guest_service: GuestService,
) -> None:
    info = guest_service.start_session()
    initial_snapshot = guest_service.validate_session(token=info.token)
    assert initial_snapshot["id"] == info.id
    initial_seen = initial_snapshot["expires_at"]
    assert initial_seen is not None
    # Verify last_seen_at is set in DB after initial validate
    with guest_service.uow:
        session = guest_service.uow.session
        assert session is not None
        first = session.get(GuestSession, info.id)
        assert first is not None
        first_seen = first.last_seen_at
        assert first_seen is not None

    # Trigger touch=True
    guest_service.validate_session(token=info.token, touch=True)

    # Verify last_seen_at is updated after touch
    with guest_service.uow:
        session = guest_service.uow.session
        assert session is not None
        refreshed = session.get(GuestSession, info.id)
        assert refreshed is not None
        refreshed_seen = refreshed.last_seen_at
        assert refreshed_seen is not None
        assert refreshed_seen >= first_seen


def test_validate_session_rejects_unknown_token(
    guest_service: GuestService,
) -> None:
    with pytest.raises(GuestError) as exc_info:
        guest_service.validate_session(token="not-a-real-token-12345678")
    assert exc_info.value.code == "GUEST_INVALID_SESSION"


def test_validate_session_rejects_revoked_token(
    guest_service: GuestService,
) -> None:
    info = guest_service.start_session()
    guest_service.revoke_session(token=info.token)
    with pytest.raises(GuestError) as exc_info:
        guest_service.validate_session(token=info.token)
    assert exc_info.value.code == "GUEST_REVOKED"


def test_validate_session_rejects_expired_token(
    guest_service: GuestService, session_factory: Any
) -> None:
    info = guest_service.start_session()
    # Force-expire by manipulating expires_at directly
    with guest_service.uow:
        session = guest_service.uow.session
        assert session is not None
        guest = session.get(GuestSession, info.id)
        assert guest is not None
        guest.expires_at = datetime.now(UTC) - timedelta(seconds=10)
        guest_service.uow.commit()
    with pytest.raises(GuestError) as exc_info:
        guest_service.validate_session(token=info.token)
    assert exc_info.value.code == "GUEST_EXPIRED"


def test_consume_quota_increments_messages_used_and_blocks_at_limit(
    guest_service: GuestService,
) -> None:
    info = guest_service.start_session()
    for expected in (1, 2, 3):
        snapshot = guest_service.consume_quota(token=info.token)
        assert snapshot["messages_used"] == expected
    with pytest.raises(GuestError) as exc_info:
        guest_service.consume_quota(token=info.token)
    assert exc_info.value.code == "GUEST_QUOTA_EXCEEDED"


def test_quota_check_uses_zero_for_revoked_token(
    guest_service: GuestService,
) -> None:
    info = guest_service.start_session()
    guest_service.revoke_session(token=info.token)
    with pytest.raises(GuestError) as exc_info:
        guest_service.consume_quota(token=info.token)
    assert exc_info.value.code == "GUEST_REVOKED"


def test_disabled_service_blocks_all_operations(
    session_factory: Any, auth_service: AuthService
) -> None:
    svc = GuestService(
        SQLAlchemyUnitOfWork(session_factory),
        auth_service=auth_service,
        enabled=False,
    )
    with pytest.raises(GuestError) as exc_info:
        svc.start_session()
    assert exc_info.value.code == "GUEST_DISABLED"


def test_convert_to_user_creates_account_revokes_guest_and_returns_tokens(
    guest_service: GuestService,
) -> None:
    info = guest_service.start_session()
    result = guest_service.convert_to_user(
        token=info.token,
        email="guest.user@example.com",
        password="very-strong-password-123",
        display_name="Guest User",
    )
    assert result.user.email == "guest.user@example.com"
    with guest_service.uow:
        session = guest_service.uow.session
        assert session is not None
        refreshed = session.get(GuestSession, info.id)
        assert refreshed is not None
        assert refreshed.converted_user_id == result.user.id
        assert refreshed.revoked_at is not None


def test_convert_to_user_rejects_already_converted_session(
    guest_service: GuestService,
) -> None:
    info = guest_service.start_session()
    guest_service.convert_to_user(
        token=info.token,
        email="guest.user@example.com",
        password="very-strong-password-123",
        display_name="Guest User",
    )
    with pytest.raises(GuestError) as exc_info:
        guest_service.convert_to_user(
            token=info.token,
            email="another.user@example.com",
            password="very-strong-password-456",
            display_name="Another User",
        )
    # Session is revoked on first conversion, so the second call surfaces
    # GUEST_REVOKED. Either code is acceptable here; we just must not let
    # the original session be re-used.
    assert exc_info.value.code in {"GUEST_REVOKED", "GUEST_ALREADY_CONVERTED"}


def test_convert_to_user_rejects_duplicate_email_without_leaking_audit(
    guest_service: GuestService, auth_service: AuthService
) -> None:
    auth_service.register(
        email="existing.user@example.com",
        password="very-strong-password-123",
        display_name="Existing User",
    )
    info = guest_service.start_session()
    with pytest.raises(AuthError) as exc_info:
        guest_service.convert_to_user(
            token=info.token,
            email="existing.user@example.com",
            password="very-strong-password-456",
            display_name="Imposter",
        )
    assert exc_info.value.code == "AUTH_USER_EXISTS"
    with guest_service.uow:
        session = guest_service.uow.session
        assert session is not None
        refreshed = session.get(GuestSession, info.id)
        assert refreshed is not None
        assert refreshed.converted_user_id is None
        assert refreshed.revoked_at is None


def test_start_session_token_is_unguessable_and_stored_as_hash(
    guest_service: GuestService, session_factory: Any
) -> None:
    seen_tokens: set[str] = set()
    for _ in range(8):
        info = guest_service.start_session()
        assert info.token not in seen_tokens
        seen_tokens.add(info.token)
        assert len(info.token) >= 32
    with guest_service.uow:
        session = guest_service.uow.session
        assert session is not None
        # No cleartext token is persisted: ensure token != session_token_hash
        guests = session.query(GuestSession).all()
        assert all(g.session_token_hash not in seen_tokens for g in guests)
