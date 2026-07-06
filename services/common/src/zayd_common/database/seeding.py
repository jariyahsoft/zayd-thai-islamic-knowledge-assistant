import hashlib
import secrets
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from sqlalchemy import select

from zayd_common.database.models import (
    Document,
    DocumentChunk,
    DocumentVersion,
    Feedback,
    Incident,
    Role,
    Source,
    SourceLicense,
    User,
    UserRole,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork


def hash_password(password: str) -> str:
    """Hash password using SHA-256 with a salt for demo seeding."""
    salt = "zayd_seed_salt_2026"
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def seed_demo_data(uow: SQLAlchemyUnitOfWork) -> dict[str, str]:
    """Seed synthetic demonstration data.

    Returns a dictionary of generated usernames/emails to plain text passwords.
    This seed command is fully idempotent.
    """
    passwords: dict[str, str] = {}

    def get_or_generate_pwd(email: str) -> str:
        # Generates a random secure password for demo credentials
        pwd = secrets.token_urlsafe(12)  # ~16 characters
        passwords[email] = pwd
        return hash_password(pwd)

    with uow:
        session = uow.session
        if session is None:
            raise RuntimeError("Database session not initialized in UoW.")

        # 1. Seed Roles
        role_names = ["admin", "reviewer", "scholar"]
        roles: dict[str, Role] = {}
        for r_name in role_names:
            role_stmt = select(Role).where(Role.name == r_name)
            existing_role = session.execute(role_stmt).scalar_one_or_none()
            if existing_role is None:
                new_role = Role(
                    id=uuid4(),
                    name=r_name,
                    description=f"{r_name.capitalize()} System Role",
                    is_system=True,
                    row_version=1,
                )
                session.add(new_role)
                roles[r_name] = new_role
            else:
                roles[r_name] = existing_role
        session.flush()

        # 2. Seed Users
        email_to_role = {
            "demo-admin@zayd.local": "admin",
            "demo-reviewer@zayd.local": "reviewer",
            "demo-scholar@zayd.local": "scholar",
        }
        users: dict[str, User] = {}
        for email, r_name in email_to_role.items():
            db_user = uow.users.get_by_email(email)
            if db_user is None:
                pwd_hash = get_or_generate_pwd(email)
                new_user = User(
                    id=uuid4(),
                    email=email,
                    display_name=f"Demo {r_name.capitalize()} (Non-Authoritative)",
                    password_hash=pwd_hash,
                    status="active",
                    mfa_enabled=False,
                    row_version=1,
                )
                uow.users.create(new_user)
                users[email] = new_user
            else:
                users[email] = db_user

        session.flush()

        # 3. Seed UserRoles (Separation of duties)
        for email, r_name in email_to_role.items():
            user = users[email]
            role = roles[r_name]
            # Check relation
            ur_stmt = (
                select(UserRole)
                .where(UserRole.user_id == user.id)
                .where(UserRole.role_id == role.id)
            )
            existing_relation = session.execute(ur_stmt).scalar_one_or_none()
            if existing_relation is None:
                user_role = UserRole(
                    user_id=user.id,
                    role_id=role.id,
                    granted_by=users["demo-admin@zayd.local"].id,
                )
                session.add(user_role)
        session.flush()

        # 4. Seed Source
        source_name = "Zayd Demo Hadith Collection [DEMO - NON-AUTHORITATIVE]"
        source_stmt = select(Source).where(Source.name == source_name)
        db_source = session.execute(source_stmt).scalar_one_or_none()
        source: Source
        if db_source is None:
            source = Source(
                id=uuid4(),
                name=source_name,
                source_type="hadith_collection",
                owner="Zayd Synthetic Datasets Team",
                website="https://github.com/deepmind/zayd",
                language="th",
                reliability_level=5,
                is_active=True,
                created_by=users["demo-admin@zayd.local"].id,
                row_version=1,
            )
            uow.sources.create(source)
        else:
            source = db_source
        session.flush()

        # 5. Seed License
        license_name = "Zayd Demo Dataset license [DEMO]"
        existing_licenses = uow.sources.get_licenses_by_source(source.id)
        license_rec = next(
            (lic for lic in existing_licenses if lic.license_name == license_name), None
        )
        if license_rec is None:
            license_rec = SourceLicense(
                id=uuid4(),
                source_id=source.id,
                license_name=license_name,
                license_version="v1.0",
                status="persistent_redistributable",
                storage_permission="allowed",
                embedding_permission="allowed",
                commercial_use="allowed",
                redistribution="allowed",
                attribution_required=True,
                attribution_template="Demo Data, DeepMind Team 2026",
                valid_from=date(2026, 1, 1),
                valid_until=date(2030, 12, 31),
                notes="Synthetic non-restricted demonstration license",
                created_by=users["demo-admin@zayd.local"].id,
                row_version=1,
            )
            uow.sources.add_license(license_rec)
        session.flush()

        # 6. Seed Document
        doc_canonical = "demo-hadith-book-1"
        db_doc = uow.documents.get_by_source_and_canonical(source.id, doc_canonical)
        doc: Document
        if db_doc is None:
            doc = Document(
                id=uuid4(),
                source_id=source.id,
                source_license_id=license_rec.id,
                canonical_id=doc_canonical,
                document_type="hadith",
                title="คู่มือข้อศรัทธาซินเธติก [DEMO - NON-AUTHORITATIVE]",
                author="ทีมออกแบบไซด์ (Zayd Team)",
                language="th",
                madhhab="shafii",
                review_status="scholar_approved",
                created_by=users["demo-admin@zayd.local"].id,
                row_version=1,
            )
            uow.documents.create(doc)
        else:
            doc = db_doc
        session.flush()

        # 7. Seed Version
        existing_versions = uow.documents.get_versions_by_document(doc.id)
        version = next((v for v in existing_versions if v.version_number == 1), None)
        if version is None:
            version = DocumentVersion(
                id=uuid4(),
                document_id=doc.id,
                version_number=1,
                status="published",
                content_hash="synthetic-content-hash-v1",
                original_file_key="seeds/hadith_demo_v1.txt",
                extracted_text="ข้อความสกัดเพื่อใช้ในการทดสอบระบบความรู้ภาษาไทยศาสนาอิสลามรุก่นอีหม่านมีหกประการประกอบด้วยศรัทธาต่ออัลลอฮ์",
                metadata_json={"source": "seed_command"},
                created_by=users["demo-admin@zayd.local"].id,
                frozen_at=datetime.now(UTC),
            )
            uow.documents.add_version(version)
            doc.published_version_id = version.id
            doc.review_status = "published"
            uow.documents.update(doc)
        session.flush()

        # 8. Seed Chunks
        existing_chunks = uow.documents.get_chunks_by_version(version.id)
        if not existing_chunks:
            chunk_0_content = (
                "[DEMO - NON-AUTHORITATIVE] บทนำ: เอกสารฉบับนี้ใช้สำหรับทดสอบการทำงาน"
                "ของระบบแชทระบุหลักฐาน (Citation) เท่านั้น เนื้อหาสังเคราะห์ขึ้นเพื่อให้"
                "กระบวนการตรวจความปลอดภัยและระบบประเมินความรู้ทำงานได้ปกติ"
            )
            chunk_0_normalized = (
                "demo non authoritative บทนำ เอกสารฉบับนี้ใช้สำหรับทดสอบการทำงาน"
                "ของระบบแชทระบุหลักฐาน citation เท่านั้น เนื้อหาสังเคราะห์ขึ้นเพื่อให้"
                "กระบวนการตรวจความปลอดภัยและระบบประเมินความรู้ทำงานได้ปกติ"
            )
            chunk_0 = DocumentChunk(
                id=uuid4(),
                document_version_id=version.id,
                chunk_index=0,
                content=chunk_0_content,
                content_normalized=chunk_0_normalized,
                token_count=45,
                page_start=1,
                page_end=1,
                section="Introduction",
                reference="Zayd-Demo-1",
                is_published=True,
                chunking_strategy_version="simple-hadith-v1",
                content_hash="chunk-hash-1",
            )
            chunk_1_content = (
                "[DEMO - NON-AUTHORITATIVE] หลักการศรัทธา (รุก่นอีหม่าน) ในศาสนาอิสลาม"
                "มีหกประการ ประการที่หนึ่งคือ การศรัทธาต่อพระผู้เป็นเจ้า (อัลลอฮ์)"
            )
            chunk_1_normalized = (
                "demo non authoritative หลักการศรัทธา รุก่นอีหม่าน ในศาสนาอิสลาม"
                "มีหกประการ ประการที่หนึ่งคือ การศรัทธาต่อพระผู้เป็นเจ้า อัลลอฮ์"
            )
            chunk_1 = DocumentChunk(
                id=uuid4(),
                document_version_id=version.id,
                chunk_index=1,
                content=chunk_1_content,
                content_normalized=chunk_1_normalized,
                token_count=40,
                page_start=1,
                page_end=1,
                section="Faith Principles",
                reference="Zayd-Demo-2",
                is_published=True,
                chunking_strategy_version="simple-hadith-v1",
                content_hash="chunk-hash-2",
            )
            uow.documents.add_chunks([chunk_0, chunk_1])
        session.flush()

        # 9. Seed Feedback and Incident (Mitigated state)
        feedback_id = UUID("00000000-0000-0000-0000-00000000fdbd")
        fb_stmt = select(Feedback).where(Feedback.id == feedback_id)
        db_fb = session.execute(fb_stmt).scalar_one_or_none()
        feedback: Feedback
        if db_fb is None:
            feedback = Feedback(
                id=feedback_id,
                category="transliteration",
                body="Demo feedback text: Minor mismatch in Thai transliteration of Arabic term.",
                status="resolved",
            )
            session.add(feedback)
        else:
            feedback = db_fb
        session.flush()

        incident_id = UUID("00000000-0000-0000-0000-00000000face")
        inc_stmt = select(Incident).where(Incident.id == incident_id)
        db_incident = session.execute(inc_stmt).scalar_one_or_none()
        if db_incident is None:
            incident = Incident(
                id=incident_id,
                feedback_id=feedback.id,
                severity="p2",
                status="resolved",
                summary="Demo: Minor mismatch in Thai transliteration of Arabic term [DEMO]",
                affected_document_id=doc.id,
                opened_by=users["demo-scholar@zayd.local"].id,
                closed_at=datetime.now(UTC),
            )
            session.add(incident)
        session.flush()

        uow.commit()

    return passwords
