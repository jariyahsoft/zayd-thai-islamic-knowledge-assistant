# Persistence Layer

## Overview

Zayd uses the Repository and Unit-of-Work (UoW) patterns to decouple domain/application services from the underlying database persistence layer. This ensures that application logic remains database-agnostic, transaction scopes are managed cleanly, and domain services cannot execute arbitrary SQL queries.

## Architecture

```
                                  +-----------------------+
                                  |  Application Service  |
                                  +-----------------------+
                                              |
                                              | Uses
                                              v
                              +-------------------------------+
                              |    AbstractUnitOfWork         |
                              +-------------------------------+
                                 |            |             |
                                 | Users      | Documents   | Instances of repositories
                                 v            v             v
       +----------------------------+  +----------------------------+
       |   AbstractUserRepository   |  | AbstractDocumentRepository |
       +----------------------------+  +----------------------------+
                     ^                               ^
                     | Implements                    | Implements
                     |                               |
       +----------------------------+  +----------------------------+
       |  SQLAlchemyUserRepository  |  |SQLAlchemyDocumentRepository|
       +----------------------------+  +----------------------------+
                     |                               |
                     +---------------+---------------+
                                     |
                                     v Uses
                               +-----------+
                               |  Session  |  SQLAlchemy DB Session
                               +-----------+
```

## Directory Structure

All persistence elements reside in the shared `zayd_common` library:

```
services/common/src/zayd_common/database/
├── __init__.py         # Engine construction and dependency setup
├── models.py           # SQLAlchemy mapper models mapping PostgreSQL tables
├── repositories.py     # Abstract repository interfaces & SQLAlchemy concrete classes
└── unit_of_work.py     # Thread-safe transaction and Unit-of-Work wrappers
```

## SQLAlchemy Models

SQLAlchemy models inherit from `Base` (compiled declarative mapping) and map core table aggregates exactly matching PostgreSQL migration constraints:

- `User` (`auth_users`)
- `Role` (`auth_roles`)
- `UserRole` (`auth_user_roles`)
- `Source` (`sources`)
- `SourceLicense` (`source_licenses`)
- `Document` (`documents`)
- `DocumentVersion` (`document_versions`)
- `DocumentChunk` (`document_chunks`)
- `Feedback` (`feedback`)
- `Incident` (`incidents`)

### Dialect Adaptability (`BaseUUID` and `BaseJSONB`)

To allow testing repository logic quickly using SQLite in-memory databases, custom SQLAlchemy `TypeDecorator` column mappers translate Postgres JSONB and UUID native fields:
- `BaseUUID`: Emits standard UUID strings when executing on SQLite, and native uuid values under PostgreSQL (parsing them back to `uuid.UUID` objects automatically).
- `BaseJSONB`: Falls back to classical `JSON` under SQLite, and maps to native `JSONB` under PostgreSQL.

## Unitable Transaction-scoped boundaries

Transaction-scoped boundaries are managed using the **Unit of Work** pattern. A session is opened during UoW enter, injected into all child repositories, and closed upon exiting the block:

```python
from zayd_common.database import get_sessionmaker, SQLAlchemyUnitOfWork

session_factory = get_sessionmaker("postgresql://zayd_dev:zayd_dev@postgres:5432/zayd_dev")

uow = SQLAlchemyUnitOfWork(session_factory)

# Enforce fail-closed transactions
with uow:
    # Operations are transaction-bound and shared under the same session
    user = uow.users.create(User(...))
    doc = uow.documents.create(Document(...))
    
    # Must explicitly commit to persist changes
    uow.commit() 
    # If the block raises an exception, rollback() is triggered automatically on exit!
```

## Mocking Repositories for Unit Testing

All repositories extend abstract interfaces (interfaces defined using Python `abc.ABC`), making them mockable for unit tests:

```python
from unittest.mock import MagicMock
from zayd_common.database import AbstractUserRepository, User

def test_service_with_mock() -> None:
    mock_repo = MagicMock(spec=AbstractUserRepository)
    mock_repo.get_by_email.return_value = User(email="mock@zayd.com", display_name="Mock")

    # Injected into application service
    user = mock_repo.get_by_email("mock@zayd.com")
    assert user.display_name == "Mock"
```

## Run Verification Tests

### Unit Tests (SQLite in-memory)

```bash
uv run pytest services/common/tests/test_database.py
```

### Integration Tests (PostgreSQL docker container)

```bash
uv run pytest services/common/tests/test_database_postgres.py
```
