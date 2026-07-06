import time
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from zayd_common.auth import AuthError, AuthService
from zayd_common.database.models import (
    AuditLog,
    AuthMfaRecoveryCode,
    Base,
    Role,
    UserRole,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.mfa import (
    MfaError,
    MfaResetChannel,
    MfaService,
    generate_totp,
    verify_totp,
)
from zayd_common.rbac import RbacService


@pytest.fixture
def services() -> tuple[AuthService, MfaService]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    return (
        AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret"),
        MfaService(SQLAlchemyUnitOfWork(session_factory)),
    )


def test_totp_round_trip_matches_current_window() -> None:
    secret = b"\x01" * 20
    timestamp = int(time.time()) // 30 * 30
    code = generate_totp(secret, timestamp=timestamp)
    assert verify_totp(secret, code=code)


def test_rejected_when_window_skips_otp() -> None:
    secret = b"\x02" * 20
    timestamp = int(time.time()) // 30 * 30 - 5 * 30
    code = generate_totp(secret, timestamp=timestamp)
    assert not verify_totp(secret, code=code)


def test_enrollment_then_confirm(services: tuple[AuthService, MfaService]) -> None:
    auth_service, mfa_service = services
    result = auth_service.register(
        email="user@example.com",
        password="very-strong-password",
        display_name="User",
    )

    enrollment = mfa_service.start_enrollment(user_id=result.user.id)
    assert len(enrollment.recovery_codes) == 10
    code = generate_totp(enrollment.secret, timestamp=int(time.time()))
    mfa_service.confirm_enrollment(user_id=result.user.id, code=code)

    assert mfa_service.is_enrolled(user_id=result.user.id)


def test_invalid_enrollment_code_is_rejected_and_audited(
    services: tuple[AuthService, MfaService],
) -> None:
    auth_service, mfa_service = services
    result = auth_service.register(
        email="user@example.com",
        password="very-strong-password",
        display_name="User",
    )
    mfa_service.start_enrollment(user_id=result.user.id)

    with pytest.raises(MfaError) as exc_info:
        mfa_service.confirm_enrollment(user_id=result.user.id, code="000000")
    assert exc_info.value.code == "MFA_INVALID_CODE"
    with mfa_service.uow:
        session = mfa_service.uow.session
        assert session is not None
        logs = session.execute(select(AuditLog)).scalars().all()
        assert any(
            log.action == "mfa.enrollment.confirm"
            and log.outcome == "failure"
            and log.reason == "invalid_code"
            for log in logs
        )


def test_recovery_code_is_single_use(services: tuple[AuthService, MfaService]) -> None:
    auth_service, mfa_service = services
    result = auth_service.register(
        email="user@example.com",
        password="very-strong-password",
        display_name="User",
    )
    enrollment = mfa_service.start_enrollment(user_id=result.user.id)
    confirm_code = generate_totp(enrollment.secret, timestamp=int(time.time()))
    mfa_service.confirm_enrollment(user_id=result.user.id, code=confirm_code)

    challenge = mfa_service.start_challenge(user_id=result.user.id)
    recovery_code = enrollment.recovery_codes[0]
    mfa_service.consume_recovery_code(
        user_id=result.user.id,
        challenge_id=challenge.challenge_id,
        recovery_code=recovery_code,
    )

    challenge_two = mfa_service.start_challenge(user_id=result.user.id)
    with pytest.raises(MfaError) as exc_info:
        mfa_service.consume_recovery_code(
            user_id=result.user.id,
            challenge_id=challenge_two.challenge_id,
            recovery_code=recovery_code,
        )
    assert exc_info.value.code == "MFA_INVALID_RECOVERY_CODE"


def test_privileged_role_without_mfa_is_blocked(
    services: tuple[AuthService, MfaService],
) -> None:
    auth_service, mfa_service = services
    result = auth_service.register(
        email="user@example.com",
        password="very-strong-password",
        display_name="User",
    )
    _grant_role_directly(mfa_service, result.user.id, "reviewer")

    with pytest.raises(MfaError) as exc_info:
        mfa_service.assert_privileged_access(user_id=result.user.id)
    assert exc_info.value.code == "MFA_PRIVILEGED_ACCESS_BLOCKED"


def test_privileged_role_with_mfa_passes_access_check(
    services: tuple[AuthService, MfaService],
) -> None:
    auth_service, mfa_service = services
    result = auth_service.register(
        email="user@example.com",
        password="very-strong-password",
        display_name="User",
    )
    _grant_role_directly(mfa_service, result.user.id, "reviewer")
    _enroll_user(mfa_service, result.user.id)

    mfa_service.assert_privileged_access(user_id=result.user.id)


def test_reset_via_recovery_code_rotates_secret_and_codes(
    services: tuple[AuthService, MfaService],
) -> None:
    auth_service, mfa_service = services
    result = auth_service.register(
        email="user@example.com",
        password="very-strong-password",
        display_name="User",
    )
    enrollment = _enroll_user(mfa_service, result.user.id)

    new_enrollment = mfa_service.reset_mfa(
        user_id=result.user.id,
        channel=MfaResetChannel.RECOVERY_CODE,
        channel_proof=enrollment.recovery_codes[0],
    )
    assert new_enrollment.secret != enrollment.secret
    assert new_enrollment.recovery_codes != enrollment.recovery_codes


def test_reset_via_password_reset_proof(services: tuple[AuthService, MfaService]) -> None:
    auth_service, mfa_service = services
    result = auth_service.register(
        email="user@example.com",
        password="very-strong-password",
        display_name="User",
    )
    _enroll_user(mfa_service, result.user.id)
    reset_token = auth_service.request_password_reset(email="user@example.com")
    assert reset_token is not None

    new_enrollment = mfa_service.reset_mfa(
        user_id=result.user.id,
        channel=MfaResetChannel.PASSWORD_RESET,
        channel_proof=reset_token,
    )
    assert new_enrollment.recovery_codes


def test_reset_audits_recovery_rotation(
    services: tuple[AuthService, MfaService],
) -> None:
    auth_service, mfa_service = services
    result = auth_service.register(
        email="user@example.com",
        password="very-strong-password",
        display_name="User",
    )
    _enroll_user(mfa_service, result.user.id)
    codes = mfa_service.rotate_recovery_codes(user_id=result.user.id)
    assert len(codes) == 10
    with mfa_service.uow:
        session = mfa_service.uow.session
        assert session is not None
        logs = session.execute(select(AuditLog)).scalars().all()
        assert any(log.action == "mfa.recovery.rotate" for log in logs)


def test_reset_without_evidence_is_rejected(
    services: tuple[AuthService, MfaService],
) -> None:
    auth_service, mfa_service = services
    result = auth_service.register(
        email="user@example.com",
        password="very-strong-password",
        display_name="User",
    )
    _enroll_user(mfa_service, result.user.id)

    with pytest.raises(MfaError) as exc_info:
        mfa_service.reset_mfa(
            user_id=result.user.id,
            channel=MfaResetChannel.RECOVERY_CODE,
            channel_proof="not-a-real-code",
        )
    assert exc_info.value.code == "MFA_INVALID_RECOVERY_CODE"


def test_existing_recovery_codes_purged_on_reset(
    services: tuple[AuthService, MfaService],
) -> None:
    auth_service, mfa_service = services
    result = auth_service.register(
        email="user@example.com",
        password="very-strong-password",
        display_name="User",
    )
    enrollment = _enroll_user(mfa_service, result.user.id)
    mfa_service.reset_mfa(
        user_id=result.user.id,
        channel=MfaResetChannel.RECOVERY_CODE,
        channel_proof=enrollment.recovery_codes[0],
    )

    with mfa_service.uow:
        session = mfa_service.uow.session
        assert session is not None
        records = (
            session.execute(
                select(AuthMfaRecoveryCode).where(AuthMfaRecoveryCode.user_id == result.user.id)
            )
            .scalars()
            .all()
        )
        assert len(records) == 10


def test_password_reset_token_is_single_use(services: tuple[AuthService, MfaService]) -> None:
    auth_service, _ = services
    auth_service.register(
        email="user@example.com",
        password="very-strong-password",
        display_name="User",
    )
    reset_token = auth_service.request_password_reset(email="user@example.com")
    assert reset_token is not None
    auth_service.reset_password(reset_token=reset_token, new_password="new-strong-password")
    with pytest.raises(AuthError) as exc_info:
        auth_service.reset_password(reset_token=reset_token, new_password="another-strong-password")
    assert exc_info.value.code == "AUTH_INVALID_RESET_TOKEN"


def test_challenge_is_invalidated_after_consumption(
    services: tuple[AuthService, MfaService],
) -> None:
    auth_service, mfa_service = services
    result = auth_service.register(
        email="user@example.com",
        password="very-strong-password",
        display_name="User",
    )
    enrollment = _enroll_user(mfa_service, result.user.id)
    challenge = mfa_service.start_challenge(user_id=result.user.id)
    code = generate_totp(enrollment.secret, timestamp=int(time.time()))
    mfa_service.verify_challenge(
        user_id=result.user.id, challenge_id=challenge.challenge_id, code=code
    )

    with pytest.raises(MfaError) as exc_info:
        mfa_service.verify_challenge(
            user_id=result.user.id, challenge_id=challenge.challenge_id, code=code
        )
    assert exc_info.value.code == "MFA_INVALID_CHALLENGE"


def _enroll_user(mfa_service: MfaService, user_id):
    enrollment = mfa_service.start_enrollment(user_id=user_id)
    code = generate_totp(enrollment.secret, timestamp=int(time.time()))
    mfa_service.confirm_enrollment(user_id=user_id, code=code)
    return enrollment


def _grant_role_directly(mfa_service: MfaService, user_id, role_name: str) -> None:
    rbac_service = RbacService(mfa_service.uow)
    rbac_service.bootstrap_system_roles()
    with _session_scope(mfa_service) as session:
        assert session is not None
        role = session.execute(select(Role).where(Role.name == role_name)).scalar_one()
        if session.get(UserRole, (user_id, role.id)) is None:
            session.add(UserRole(user_id=user_id, role_id=role.id, granted_by=user_id))
        session.commit()


@contextmanager
def _session_scope(mfa_service: MfaService) -> Iterator[Session]:
    session = mfa_service.uow.session_factory()
    try:
        yield session
    finally:
        session.close()
