from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from zayd_common.database.models import (
    Document,
    DocumentChunk,
    DocumentVersion,
    Incident,
    Source,
    SourceLicense,
    User,
)


class AbstractUserRepository(ABC):
    """Abstract interface for User repository operations."""

    @abstractmethod
    def get_by_id(self, user_id: UUID) -> User | None:
        pass

    @abstractmethod
    def get_by_email(self, email: str) -> User | None:
        pass

    @abstractmethod
    def create(self, user: User) -> User:
        pass

    @abstractmethod
    def update(self, user: User) -> User:
        pass

    @abstractmethod
    def get_users(self) -> Sequence[User]:
        pass


class SQLAlchemyUserRepository(AbstractUserRepository):
    """SQLAlchemy implementation of the User repository."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, user_id: UUID) -> User | None:
        return self.session.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return self.session.execute(stmt).scalar_one_or_none()

    def create(self, user: User) -> User:
        self.session.add(user)
        return user

    def update(self, user: User) -> User:
        # Pushes any changes to the DB session; doesn't commit
        self.session.flush()
        return user

    def get_users(self) -> Sequence[User]:
        stmt = select(User).where(User.deleted_at.is_(None))
        return self.session.execute(stmt).scalars().all()


class AbstractSourceRepository(ABC):
    """Abstract interface for Source repository operations."""

    @abstractmethod
    def get_by_id(self, source_id: UUID) -> Source | None:
        pass

    @abstractmethod
    def create(self, source: Source) -> Source:
        pass

    @abstractmethod
    def update(self, source: Source) -> Source:
        pass

    @abstractmethod
    def add_license(self, license_record: SourceLicense) -> SourceLicense:
        pass

    @abstractmethod
    def get_license_by_id(self, license_id: UUID) -> SourceLicense | None:
        pass

    @abstractmethod
    def get_licenses_by_source(self, source_id: UUID) -> Sequence[SourceLicense]:
        pass

    @abstractmethod
    def get_sources(self) -> Sequence[Source]:
        pass


class SQLAlchemySourceRepository(AbstractSourceRepository):
    """SQLAlchemy implementation of the Source repository."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, source_id: UUID) -> Source | None:
        return self.session.get(Source, source_id)

    def create(self, source: Source) -> Source:
        self.session.add(source)
        return source

    def update(self, source: Source) -> Source:
        self.session.flush()
        return source

    def add_license(self, license_record: SourceLicense) -> SourceLicense:
        self.session.add(license_record)
        return license_record

    def get_license_by_id(self, license_id: UUID) -> SourceLicense | None:
        return self.session.get(SourceLicense, license_id)

    def get_licenses_by_source(self, source_id: UUID) -> Sequence[SourceLicense]:
        stmt = select(SourceLicense).where(SourceLicense.source_id == source_id)
        return self.session.execute(stmt).scalars().all()

    def get_sources(self) -> Sequence[Source]:
        stmt = select(Source).where(Source.deleted_at.is_(None))
        return self.session.execute(stmt).scalars().all()


class AbstractDocumentRepository(ABC):
    """Abstract interface for Document repository operations."""

    @abstractmethod
    def get_by_id(self, document_id: UUID) -> Document | None:
        pass

    @abstractmethod
    def get_by_source_and_canonical(self, source_id: UUID, canonical_id: str) -> Document | None:
        pass

    @abstractmethod
    def create(self, document: Document) -> Document:
        pass

    @abstractmethod
    def update(self, document: Document) -> Document:
        pass

    @abstractmethod
    def add_version(self, version: DocumentVersion) -> DocumentVersion:
        pass

    @abstractmethod
    def get_version_by_id(self, version_id: UUID) -> DocumentVersion | None:
        pass

    @abstractmethod
    def get_versions_by_document(self, document_id: UUID) -> Sequence[DocumentVersion]:
        pass

    @abstractmethod
    def add_chunks(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        pass

    @abstractmethod
    def get_chunks_by_version(self, version_id: UUID) -> Sequence[DocumentChunk]:
        pass

    @abstractmethod
    def get_documents(self) -> Sequence[Document]:
        pass


class SQLAlchemyDocumentRepository(AbstractDocumentRepository):
    """SQLAlchemy implementation of the Document repository."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, document_id: UUID) -> Document | None:
        return self.session.get(Document, document_id)

    def get_by_source_and_canonical(self, source_id: UUID, canonical_id: str) -> Document | None:
        stmt = (
            select(Document)
            .where(Document.source_id == source_id)
            .where(Document.canonical_id == canonical_id)
            .where(Document.deleted_at.is_(None))
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def create(self, document: Document) -> Document:
        self.session.add(document)
        return document

    def update(self, document: Document) -> Document:
        self.session.flush()
        return document

    def add_version(self, version: DocumentVersion) -> DocumentVersion:
        self.session.add(version)
        return version

    def get_version_by_id(self, version_id: UUID) -> DocumentVersion | None:
        return self.session.get(DocumentVersion, version_id)

    def get_versions_by_document(self, document_id: UUID) -> Sequence[DocumentVersion]:
        stmt = select(DocumentVersion).where(DocumentVersion.document_id == document_id)
        return self.session.execute(stmt).scalars().all()

    def add_chunks(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        self.session.add_all(chunks)
        return chunks

    def get_chunks_by_version(self, version_id: UUID) -> Sequence[DocumentChunk]:
        stmt = select(DocumentChunk).where(DocumentChunk.document_version_id == version_id)
        return self.session.execute(stmt).scalars().all()

    def get_documents(self) -> Sequence[Document]:
        stmt = select(Document).where(Document.deleted_at.is_(None))
        return self.session.execute(stmt).scalars().all()


class AbstractIncidentRepository(ABC):
    """Abstract interface for Incident repository operations."""

    @abstractmethod
    def get_by_id(self, incident_id: UUID) -> Incident | None:
        pass

    @abstractmethod
    def create(self, incident: Incident) -> Incident:
        pass

    @abstractmethod
    def update(self, incident: Incident) -> Incident:
        pass

    @abstractmethod
    def get_incidents(self) -> Sequence[Incident]:
        pass


class SQLAlchemyIncidentRepository(AbstractIncidentRepository):
    """SQLAlchemy implementation of the Incident repository."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, incident_id: UUID) -> Incident | None:
        return self.session.get(Incident, incident_id)

    def create(self, incident: Incident) -> Incident:
        self.session.add(incident)
        return incident

    def update(self, incident: Incident) -> Incident:
        self.session.flush()
        return incident

    def get_incidents(self) -> Sequence[Incident]:
        stmt = select(Incident)
        return self.session.execute(stmt).scalars().all()
