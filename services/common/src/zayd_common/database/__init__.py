from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from zayd_common.database.models import (
    AuditLog,
    AuthPermission,
    Base,
    Role,
    RolePermission,
    UserRole,
)
from zayd_common.database.repositories import (
    AbstractDocumentRepository,
    AbstractIncidentRepository,
    AbstractSourceRepository,
    AbstractUserRepository,
    SQLAlchemyDocumentRepository,
    SQLAlchemyIncidentRepository,
    SQLAlchemySourceRepository,
    SQLAlchemyUserRepository,
)
from zayd_common.database.seeding import seed_demo_data
from zayd_common.database.unit_of_work import AbstractUnitOfWork, SQLAlchemyUnitOfWork


def get_sessionmaker(database_url: str) -> sessionmaker[Session]:
    """Create a SQLAlchemy sessionmaker with pre-configured settings."""
    # Use pool_pre_ping=True to automatically handle disconnected DB connections
    engine = create_engine(database_url, pool_pre_ping=True)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


__all__ = [
    "AuditLog",
    "AuthPermission",
    "Base",
    "Role",
    "RolePermission",
    "UserRole",
    "AbstractUserRepository",
    "SQLAlchemyUserRepository",
    "AbstractSourceRepository",
    "SQLAlchemySourceRepository",
    "AbstractDocumentRepository",
    "SQLAlchemyDocumentRepository",
    "AbstractIncidentRepository",
    "SQLAlchemyIncidentRepository",
    "AbstractUnitOfWork",
    "SQLAlchemyUnitOfWork",
    "get_sessionmaker",
    "seed_demo_data",
]
