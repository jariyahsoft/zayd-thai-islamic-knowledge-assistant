from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from zayd_common.database.models import AuditLog, Base, User
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.user_preferences import (
    DEFAULT_MADHHAB,
    UserPreferencesError,
    UserPreferencesService,
    UserPreferencesUpdate,
)


@pytest.fixture
def preferences_fixture() -> tuple[UserPreferencesService, sessionmaker, User]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    user_id = uuid4()
    with session_factory() as session:
        session.add(
            User(
                id=user_id,
                email="prefs@example.test",
                display_name="Prefs User",
            )
        )
        session.commit()
        user = session.get(User, user_id)
        assert user is not None
    service = UserPreferencesService(SQLAlchemyUnitOfWork(session_factory))
    with session_factory() as session:
        user = session.get(User, user_id)
        assert user is not None
        return service, session_factory, user


def test_get_preferences_discloses_default_shafii(
    preferences_fixture: tuple[UserPreferencesService, sessionmaker, User],
) -> None:
    service, _session_factory, user = preferences_fixture
    preferences = service.get_preferences(user_id=user.id)
    assert preferences.madhhab == DEFAULT_MADHHAB
    assert preferences.default_madhhab == DEFAULT_MADHHAB


def test_update_preferences_persists_values(
    preferences_fixture: tuple[UserPreferencesService, sessionmaker, User],
) -> None:
    service, _session_factory, user = preferences_fixture
    updated = service.update_preferences(
        user_id=user.id,
        update=UserPreferencesUpdate(
            madhhab="hanafi",
            answer_length="detailed",
            show_arabic=False,
            history_mode="disabled",
        ),
        trace_id="trace-preferences",
    )
    assert updated.madhhab == "hanafi"
    assert updated.answer_length == "detailed"
    assert updated.show_arabic is False
    assert updated.history_mode == "disabled"

    reread = service.get_preferences(user_id=user.id)
    assert reread.madhhab == "hanafi"
    assert reread.answer_length == "detailed"


def test_update_preferences_rejects_invalid_values(
    preferences_fixture: tuple[UserPreferencesService, sessionmaker, User],
) -> None:
    service, _session_factory, user = preferences_fixture
    with pytest.raises(UserPreferencesError, match="madhhab"):
        service.update_preferences(
            user_id=user.id,
            update=UserPreferencesUpdate(madhhab="invalid"),
        )


def test_update_preferences_writes_audit_log(
    preferences_fixture: tuple[UserPreferencesService, sessionmaker, User],
) -> None:
    service, session_factory, user = preferences_fixture
    service.update_preferences(
        user_id=user.id,
        update=UserPreferencesUpdate(answer_length="short"),
        trace_id="trace-audit",
    )
    with session_factory() as session:
        audits = session.scalars(select(AuditLog)).all()
    assert len(audits) == 1
    assert audits[0].action == "users.preferences.update"