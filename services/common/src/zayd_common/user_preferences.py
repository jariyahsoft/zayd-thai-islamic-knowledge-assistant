"""User-facing application preferences."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from zayd_common.database.models import AuditLog, User
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

DEFAULT_MADHHAB = "shafii"
DEFAULT_ANSWER_LENGTH = "normal"
DEFAULT_HISTORY_MODE = "enabled"
DEFAULT_SHOW_ARABIC = True

UserPreferencesErrorCode = Literal[
    "PREFERENCES_INVALID",
    "PREFERENCES_USER_NOT_FOUND",
]

ALLOWED_MADHHABS = frozenset({"shafii", "hanafi", "maliki", "hanbali"})
ALLOWED_ANSWER_LENGTHS = frozenset({"short", "normal", "detailed"})
ALLOWED_HISTORY_MODES = frozenset({"enabled", "disabled"})


class UserPreferencesError(Exception):
    def __init__(
        self,
        code: UserPreferencesErrorCode,
        message: str,
        *,
        status_code: int = 400,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class UserPreferencesPublic:
    madhhab: str
    default_madhhab: str
    answer_length: str
    show_arabic: bool
    history_mode: str
    preferred_language: str
    synced: bool = True


@dataclass(frozen=True)
class UserPreferencesUpdate:
    madhhab: str | None = None
    answer_length: str | None = None
    show_arabic: bool | None = None
    history_mode: str | None = None


class UserPreferencesService:
    def __init__(self, uow: SQLAlchemyUnitOfWork) -> None:
        self.uow = uow

    def get_preferences(self, *, user_id: UUID) -> UserPreferencesPublic:
        with self.uow:
            user = self._get_user(user_id)
            public = _public(user)
            self.uow.commit()
            return public

    def update_preferences(
        self,
        *,
        user_id: UUID,
        update: UserPreferencesUpdate,
        trace_id: str | None = None,
    ) -> UserPreferencesPublic:
        with self.uow:
            user = self._get_user(user_id)
            before = _public(user)
            if update.madhhab is not None:
                _validate_madhhab(update.madhhab)
                user.preferred_madhhab = update.madhhab
            if update.answer_length is not None:
                _validate_answer_length(update.answer_length)
                user.answer_length = update.answer_length
            if update.show_arabic is not None:
                user.show_arabic = update.show_arabic
            if update.history_mode is not None:
                _validate_history_mode(update.history_mode)
                user.history_mode = update.history_mode
            after = _public(user)
            self._audit_update(
                actor_user_id=user_id,
                before=before,
                after=after,
                trace_id=trace_id,
            )
            self.uow.commit()
            return after

    def _get_user(self, user_id: UUID) -> User:
        if self.uow.session is None:
            raise RuntimeError("Database session not initialised in UoW.")
        user = self.uow.session.get(User, user_id)
        if user is None or user.deleted_at is not None:
            raise UserPreferencesError(
                "PREFERENCES_USER_NOT_FOUND",
                "User was not found.",
                status_code=404,
            )
        return user

    def _audit_update(
        self,
        *,
        actor_user_id: UUID,
        before: UserPreferencesPublic,
        after: UserPreferencesPublic,
        trace_id: str | None,
    ) -> None:
        if self.uow.session is None:
            return
        self.uow.session.add(
            AuditLog(
                actor_user_id=actor_user_id,
                action="users.preferences.update",
                resource_type="user",
                resource_id=actor_user_id,
                outcome="success",
                request_id=trace_id,
                trace_id=trace_id,
                before_summary={
                    "madhhab": before.madhhab,
                    "answer_length": before.answer_length,
                    "show_arabic": before.show_arabic,
                    "history_mode": before.history_mode,
                },
                after_summary={
                    "madhhab": after.madhhab,
                    "answer_length": after.answer_length,
                    "show_arabic": after.show_arabic,
                    "history_mode": after.history_mode,
                },
            )
        )


def _public(user: User) -> UserPreferencesPublic:
    return UserPreferencesPublic(
        madhhab=user.preferred_madhhab,
        default_madhhab=DEFAULT_MADHHAB,
        answer_length=getattr(user, "answer_length", DEFAULT_ANSWER_LENGTH),
        show_arabic=getattr(user, "show_arabic", DEFAULT_SHOW_ARABIC),
        history_mode=getattr(user, "history_mode", DEFAULT_HISTORY_MODE),
        preferred_language=user.preferred_language,
    )


def _validate_madhhab(value: str) -> None:
    normalized = value.strip().lower()
    if normalized not in ALLOWED_MADHHABS:
        raise UserPreferencesError(
            "PREFERENCES_INVALID",
            "madhhab must be shafii, hanafi, maliki, or hanbali.",
            status_code=400,
        )


def _validate_answer_length(value: str) -> None:
    normalized = value.strip().lower()
    if normalized not in ALLOWED_ANSWER_LENGTHS:
        raise UserPreferencesError(
            "PREFERENCES_INVALID",
            "answer_length must be short, normal, or detailed.",
            status_code=400,
        )


def _validate_history_mode(value: str) -> None:
    normalized = value.strip().lower()
    if normalized not in ALLOWED_HISTORY_MODES:
        raise UserPreferencesError(
            "PREFERENCES_INVALID",
            "history_mode must be enabled or disabled.",
            status_code=400,
        )