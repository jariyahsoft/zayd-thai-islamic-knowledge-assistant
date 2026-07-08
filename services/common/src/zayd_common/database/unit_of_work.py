from abc import ABC, abstractmethod
from types import TracebackType

from sqlalchemy.orm import Session, sessionmaker

from zayd_common.database.repositories import (
    AbstractDocumentRepository,
    AbstractIncidentRepository,
    AbstractReviewTaskRepository,
    AbstractSourceRepository,
    AbstractUserRepository,
    SQLAlchemyDocumentRepository,
    SQLAlchemyIncidentRepository,
    SQLAlchemyReviewTaskRepository,
    SQLAlchemySourceRepository,
    SQLAlchemyUserRepository,
)


class AbstractUnitOfWork(ABC):
    """Abstract interface for Unit of Work transaction boundary."""

    users: AbstractUserRepository
    sources: AbstractSourceRepository
    documents: AbstractDocumentRepository
    incidents: AbstractIncidentRepository
    review_tasks: AbstractReviewTaskRepository

    def __enter__(self) -> "AbstractUnitOfWork":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.rollback()

    @abstractmethod
    def commit(self) -> None:
        pass

    @abstractmethod
    def rollback(self) -> None:
        pass


class SQLAlchemyUnitOfWork(AbstractUnitOfWork):
    """SQLAlchemy implementation of Unit of Work."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory
        self.session: Session | None = None

    def __enter__(self) -> "SQLAlchemyUnitOfWork":
        self.session = self.session_factory()
        self.users = SQLAlchemyUserRepository(self.session)
        self.sources = SQLAlchemySourceRepository(self.session)
        self.documents = SQLAlchemyDocumentRepository(self.session)
        self.incidents = SQLAlchemyIncidentRepository(self.session)
        self.review_tasks = SQLAlchemyReviewTaskRepository(self.session)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        try:
            super().__exit__(exc_type, exc_val, exc_tb)
        finally:
            if self.session is not None:
                self.session.close()

    def commit(self) -> None:
        if self.session is not None:
            self.session.commit()

    def rollback(self) -> None:
        if self.session is not None:
            self.session.rollback()
