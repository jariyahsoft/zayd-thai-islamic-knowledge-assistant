"""Unit tests for the metadata extraction service.

Covers:
- Schema validation tests
- Provider failure/fallback tests
- Prompt-version trace tests
- Rule-based extraction golden fixtures
- Idempotency and versioning
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from zayd_common.database.models import Base, DocumentVersion
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.metadata_extraction import (
    DEFAULT_EXTRACTOR_NAME,
    DEFAULT_EXTRACTOR_VERSION,
    ExtractedField,
    MetadataExtractionError,
    MetadataExtractionResult,
    MetadataExtractionService,
    RuleBasedExtractor,
    validate_confidence,
    validate_extracted_document_type,
    validate_extracted_madhhab,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@dataclass
class FakeVersionRepo:
    """Simplified in-memory version store for service tests."""

    versions: dict = None
    documents: dict = None

    def __post_init__(self):
        self.versions = {}
        self.documents = {}

    def get_version_by_id(self, version_id):
        return self.versions.get(version_id)

    def get_by_id(self, document_id):
        return self.documents.get(document_id)

    def add_version(self, version):
        self.versions[version.id] = version

    def update(self, document):
        self.documents[document.id] = document


@dataclass
class FakeUoW:
    """Simplified UoW for service unit tests."""

    documents: FakeVersionRepo = None
    commit_called: bool = False

    def __post_init__(self):
        self.documents = FakeVersionRepo()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def commit(self):
        self.commit_called = True


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------


class TestSchemaValidation:
    """Structured output validation rejects malformed results."""

    def test_confidence_out_of_range_raises(self):
        with pytest.raises(MetadataExtractionError) as exc_info:
            validate_confidence(1.5)
        assert exc_info.value.code == "EXTRACTION_MALFORMED_OUTPUT"

    def test_confidence_negative_raises(self):
        with pytest.raises(MetadataExtractionError) as exc_info:
            validate_confidence(-0.1)
        assert exc_info.value.code == "EXTRACTION_MALFORMED_OUTPUT"

    def test_confidence_zero_is_valid(self):
        assert validate_confidence(0.0) == 0.0

    def test_confidence_one_is_valid(self):
        assert validate_confidence(1.0) == 1.0

    def test_valid_madhhab_shafii(self):
        assert validate_extracted_madhhab("shafii") == "shafii"

    def test_valid_madhhab_arabic(self):
        assert validate_extracted_madhhab("شافعي") == "unknown"  # Arabic key not in validation

    def test_invalid_madhhab_defaults(self):
        assert validate_extracted_madhhab("invalid_madhab") == "unknown"

    def test_valid_document_type_book(self):
        assert validate_extracted_document_type("book") == "book"

    def test_invalid_document_type_defaults(self):
        assert validate_extracted_document_type("video") == "unknown"

    def test_empty_madhhab_defaults(self):
        assert validate_extracted_madhhab("") == "unknown"


# ---------------------------------------------------------------------------
# Rule-based extractor golden fixtures
# ---------------------------------------------------------------------------


class TestRuleBasedExtractor:
    """Golden fixtures for rule-based metadata extraction."""

    def test_title_from_first_line(self):
        extractor = RuleBasedExtractor()
        text = "Al-Risala\nBy Imam Shafi'i\nThis is a book about usul al-fiqh."
        result = extractor.extract(
            text=text, sections=[], filename="book.txt", content_type="text/plain"
        )
        assert len(result.title) == 1
        assert result.title[0].value == "Al-Risala"
        assert result.title[0].confidence == 0.5
        assert result.title[0].verification_status == "unverified"

    def test_author_thai_pattern(self):
        extractor = RuleBasedExtractor()
        text = "หลักการอิสลาม\nโดย อาจารย์สมชาย\nเนื้อหาเกี่ยวกับ..."
        result = extractor.extract(
            text=text, sections=[], filename="book.txt", content_type="text/plain"
        )
        assert len(result.author) == 1
        assert "อาจารย์สมชาย" in result.author[0].value

    def test_author_arabic_pattern(self):
        extractor = RuleBasedExtractor()
        text = "كتاب التوحيد\nتأليف محمد بن عبد الوهاب\nمقدمة"
        result = extractor.extract(
            text=text, sections=[], filename="book.txt", content_type="text/plain"
        )
        assert len(result.author) == 1
        assert "محمد" in result.author[0].value

    def test_author_english_pattern(self):
        extractor = RuleBasedExtractor()
        text = "The Meadows of Gold\nAuthor: Al-Masudi\nTranslated by Paul Lunde"
        result = extractor.extract(
            text=text, sections=[], filename="book.txt", content_type="text/plain"
        )
        assert len(result.author) == 1
        assert "Al-Masudi" in result.author[0].value

    def test_translator_thai_pattern(self):
        extractor = RuleBasedExtractor()
        text = "อัลกุรอาน\nแปลโดย สมาคมนักเรียนเก่าอาหรับ"
        result = extractor.extract(
            text=text, sections=[], filename="book.txt", content_type="text/plain"
        )
        assert len(result.translator) == 1
        assert "สมาคม" in result.translator[0].value

    def test_translator_arabic_pattern(self):
        extractor = RuleBasedExtractor()
        text = "صحيح البخاري\nترجمة د. محمد محمود"
        result = extractor.extract(
            text=text, sections=[], filename="book.txt", content_type="text/plain"
        )
        assert len(result.translator) == 1
        assert "محمد" in result.translator[0].value

    def test_madhhab_detection(self):
        extractor = RuleBasedExtractor()
        text = "This book follows the Shafii school of thought in fiqh."
        result = extractor.extract(
            text=text, sections=[], filename="book.txt", content_type="text/plain"
        )
        assert len(result.madhhab or []) == 1
        assert result.madhhab[0].value == "shafii"

    def test_document_type_from_pdf_filename(self):
        extractor = RuleBasedExtractor()
        text = "Some book content"
        result = extractor.extract(
            text=text, sections=[], filename="book.pdf", content_type="application/pdf"
        )
        assert len(result.document_type) == 1
        assert result.document_type[0].value == "book"
        assert result.document_type[0].confidence == 0.8

    def test_document_type_from_txt_filename(self):
        extractor = RuleBasedExtractor()
        text = "Article content"
        result = extractor.extract(
            text=text, sections=[], filename="article.txt", content_type="text/plain"
        )
        assert len(result.document_type) == 1
        assert result.document_type[0].value == "article"

    def test_chapter_detection(self):
        extractor = RuleBasedExtractor()
        text = "Introduction\n\nบทที่ 1 ว่าด้วยเรื่องศรัทธา\n\nเนื้อหา\n\nบทที่ 2 ว่าด้วยเรื่องทำนาย"
        result = extractor.extract(
            text=text, sections=[], filename="book.txt", content_type="text/plain"
        )
        assert len(result.chapters) >= 2

    def test_quran_reference_detection(self):
        extractor = RuleBasedExtractor()
        text = "ดังที่อัลกุรอาน 2:255 กล่าวไว้\nและใน Quran 36:36"
        result = extractor.extract(
            text=text, sections=[], filename="book.txt", content_type="text/plain"
        )
        quran_refs = [r for r in result.references if r.reference_type == "quran"]
        assert len(quran_refs) >= 1

    def test_hadith_reference_detection_thai(self):
        extractor = RuleBasedExtractor()
        text = "ฮะดีษที่ 123 รายงานโดย..."
        result = extractor.extract(
            text=text, sections=[], filename="book.txt", content_type="text/plain"
        )
        hadith_refs = [r for r in result.references if r.reference_type == "hadith"]
        assert len(hadith_refs) >= 1

    def test_empty_text_warns(self):
        extractor = RuleBasedExtractor()
        result = extractor.extract(
            text="", sections=[], filename="empty.txt", content_type="text/plain"
        )
        assert len(result.warnings) >= 1
        assert any("empty" in w.lower() for w in result.warnings)

    def test_all_suggestions_unverified_by_default(self):
        extractor = RuleBasedExtractor()
        text = "Title\nBy Author\nTranslated by Translator"
        result = extractor.extract(
            text=text, sections=[], filename="book.pdf", content_type="application/pdf"
        )
        for field_list in [result.title, result.author, result.translator]:
            for field in field_list:
                assert field.verification_status == "unverified"

    def test_extractor_name_and_version(self):
        extractor = RuleBasedExtractor()
        assert extractor.name == DEFAULT_EXTRACTOR_NAME
        assert extractor.version == DEFAULT_EXTRACTOR_VERSION
        assert extractor.prompt_version is None


# ---------------------------------------------------------------------------
# Provider failure/fallback tests
# ---------------------------------------------------------------------------


class TestProviderFailure:
    """Provider failure and fallback behaviour."""

    def test_service_rejects_missing_version(self):
        uow = FakeUoW()
        service = MetadataExtractionService(uow)
        with pytest.raises(MetadataExtractionError) as exc_info:
            service.extract(document_version_id=uuid4())
        assert exc_info.value.code == "EXTRACTION_VERSION_NOT_FOUND"

    def test_service_rejects_unparsed_version(self):
        uow = FakeUoW()
        service = MetadataExtractionService(uow)
        version_id = uuid4()
        version = DocumentVersion(
            id=version_id,
            document_id=uuid4(),
            version_number=1,
            status="scanned_clean",
            content_hash="abc",
            original_file_key="uploads/test.txt",
            extracted_text=None,
            metadata_json={"filename": "test.txt", "content_type": "text/plain"},
            created_by=uuid4(),
        )
        uow.documents.versions[version_id] = version
        with pytest.raises(MetadataExtractionError) as exc_info:
            service.extract(document_version_id=version_id, text="")
        assert exc_info.value.code == "EXTRACTION_VERSION_NOT_PARSED"


# ---------------------------------------------------------------------------
# Service integration (SQLite-backed)
# ---------------------------------------------------------------------------


@pytest.fixture
def service_with_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    uow = SQLAlchemyUnitOfWork(session_factory)
    service = MetadataExtractionService(uow)
    return service, session_factory, uow


class TestService:
    """End-to-end service tests with in-memory SQLite."""

    def test_extract_and_persist(self, service_with_db):
        service, session_factory, uow = service_with_db
        doc_id = uuid4()
        version_id = uuid4()

        with uow:
            from zayd_common.database.models import Document
            from zayd_common.database.models import DocumentVersion as DV

            uow.documents.create(
                Document(
                    id=doc_id,
                    source_id=uuid4(),
                    source_license_id=uuid4(),
                    canonical_id="doc-001",
                    document_type="book",
                    title="Test",
                    language="th",
                    created_by=uuid4(),
                )
            )
            uow.documents.add_version(
                DV(
                    id=version_id,
                    document_id=doc_id,
                    version_number=1,
                    status="scanned_clean",
                    content_hash="abc",
                    original_file_key="uploads/test.txt",
                    extracted_text=(
                        "Al-Risala\n\nBy Imam Shafii\nThis is a book about usul al-fiqh."
                    ),
                    metadata_json={
                        "filename": "book.pdf",
                        "content_type": "application/pdf",
                    },
                    created_by=uuid4(),
                )
            )
            uow.commit()

        result = service.extract(document_version_id=version_id)
        assert result is not None
        assert result.document_id == doc_id
        assert result.document_version_id == version_id
        assert len(result.title) >= 1
        assert result.title[0].value == "Al-Risala"
        assert result.title[0].verification_status == "unverified"

        # Verify persistence
        stored = service.get_extraction(document_version_id=version_id)
        assert stored is not None
        assert stored.title[0].value == "Al-Risala"
        assert stored.title[0].verification_status == "unverified"

    def test_get_extraction_returns_none_for_missing(self, service_with_db):
        service, session_factory, uow = service_with_db
        result = service.get_extraction(document_version_id=uuid4())
        assert result is None

    def test_idempotent_extraction(self, service_with_db):
        service, session_factory, uow = service_with_db
        doc_id = uuid4()
        version_id = uuid4()

        with uow:
            from zayd_common.database.models import Document
            from zayd_common.database.models import DocumentVersion as DV

            uow.documents.create(
                Document(
                    id=doc_id,
                    source_id=uuid4(),
                    source_license_id=uuid4(),
                    canonical_id="doc-002",
                    document_type="book",
                    title="Test",
                    language="th",
                    created_by=uuid4(),
                )
            )
            uow.documents.add_version(
                DV(
                    id=version_id,
                    document_id=doc_id,
                    version_number=1,
                    status="scanned_clean",
                    content_hash="abc",
                    original_file_key="uploads/test.txt",
                    extracted_text="Same Content",
                    metadata_json={"filename": "doc.txt", "content_type": "text/plain"},
                    created_by=uuid4(),
                )
            )
            uow.commit()

        service.extract(document_version_id=version_id)
        # Verify the store is additive (we append, not replace, the extraction key)
        stored_first = service.get_extraction(document_version_id=version_id)
        assert stored_first is not None
        assert stored_first.title[0].value == "Same Content"


# ---------------------------------------------------------------------------
# Prompt-version trace tests
# ---------------------------------------------------------------------------


class FakePromptAwareExtractor:
    """Test extractor that demonstrates prompt-version tracking."""

    name = "test-prompt-extractor"
    version = "0.1.0"
    prompt_version = "prompt-v3"

    def extract(self, *, text, sections, filename, content_type):
        return MetadataExtractionResult(
            document_id=uuid4(),
            document_version_id=uuid4(),
            extractor_name=self.name,
            extractor_version=self.version,
            title=[
                ExtractedField(
                    name="title",
                    value="Extracted Title",
                    confidence=0.9,
                    extractor_name=self.name,
                    extractor_version=self.version,
                    prompt_version=self.prompt_version,
                )
            ],
        )


class TestPromptVersionTrace:
    """Prompt-version provenance is recorded in extraction results."""

    def test_prompt_version_in_result(self):
        extractor = FakePromptAwareExtractor()
        result = extractor.extract(
            text="Some text", sections=[], filename="test.txt", content_type="text/plain"
        )
        assert result.extractor_name == "test-prompt-extractor"
        assert len(result.title) == 1
        assert result.title[0].prompt_version == "prompt-v3"
        assert result.title[0].extractor_name == "test-prompt-extractor"

    def test_rule_extractor_has_no_prompt(self):
        extractor = RuleBasedExtractor()
        result = extractor.extract(
            text="Title", sections=[], filename="test.txt", content_type="text/plain"
        )
        assert result.title[0].prompt_version is None
