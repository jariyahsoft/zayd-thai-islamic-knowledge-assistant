"""Tests for S3-compatible object storage."""

from __future__ import annotations

import os
import uuid
from urllib.request import Request, urlopen

import pytest
from botocore.exceptions import ClientError
from zayd_common.storage import (
    DEFAULT_SIGNED_URL_TTL_SECONDS,
    MAX_SIGNED_URL_TTL_SECONDS,
    S3ObjectStorage,
    S3StorageSettings,
    StorageError,
)


class FakeBody:
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.closed = False

    def read(self) -> bytes:
        return self.content

    def close(self) -> None:
        self.closed = True


class FakeS3Client:
    def __init__(self) -> None:
        self.put_calls: list[dict[str, object]] = []
        self.deleted_keys: list[str] = []
        self.fail_put = False
        self.fail_get = False
        self.objects: dict[str, bytes] = {}

    def put_object(self, **kwargs: object) -> None:
        if self.fail_put:
            raise ClientError({"Error": {"Code": "SlowDown", "Message": "retry"}}, "PutObject")
        self.put_calls.append(kwargs)
        self.objects[str(kwargs["Key"])] = bytes(kwargs["Body"])

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, object]:
        if self.fail_get:
            raise ClientError({"Error": {"Code": "NoSuchKey", "Message": "missing"}}, "GetObject")
        return {"Body": FakeBody(self.objects[Key])}

    def delete_object(self, *, Bucket: str, Key: str) -> None:
        self.deleted_keys.append(Key)

    def generate_presigned_url(
        self, *, ClientMethod: str, Params: dict[str, object], ExpiresIn: int
    ) -> str:
        return (
            "https://storage.example.local/"
            f"{Params['Bucket']}/{Params['Key']}?ttl={ExpiresIn}&method={ClientMethod}"
        )


def test_put_private_bytes_uses_bucket_and_metadata() -> None:
    client = FakeS3Client()
    storage = S3ObjectStorage(_settings(), client=client)

    object_ref = storage.put_private_bytes(
        key="uploads/quarantine/doc/test.pdf",
        content=b"hello",
        content_type="application/pdf",
        metadata={"document_id": "doc"},
    )

    assert object_ref.bucket == "zayd-private"
    assert object_ref.key == "uploads/quarantine/doc/test.pdf"
    assert client.put_calls[0]["Bucket"] == "zayd-private"
    assert client.put_calls[0]["Metadata"] == {"document_id": "doc"}


def test_signed_url_ttl_is_bounded() -> None:
    client = FakeS3Client()
    storage = S3ObjectStorage(_settings(signed_url_ttl_seconds=120), client=client)

    signed = storage.create_signed_get_url(
        key="uploads/quarantine/doc/test.pdf",
        filename="test.pdf",
        content_type="application/pdf",
        expires_in_seconds=DEFAULT_SIGNED_URL_TTL_SECONDS,
    )

    assert signed.expires_in_seconds == 120
    assert "ttl=120" in signed.url


def test_get_private_bytes_reads_quarantine_object() -> None:
    client = FakeS3Client()
    storage = S3ObjectStorage(_settings(), client=client)
    storage.put_private_bytes(
        key="uploads/quarantine/doc/test.pdf",
        content=b"scan-me",
        content_type="application/pdf",
    )

    assert storage.get_private_bytes(key="uploads/quarantine/doc/test.pdf") == b"scan-me"


def test_get_failure_returns_stable_error() -> None:
    client = FakeS3Client()
    client.fail_get = True
    storage = S3ObjectStorage(_settings(), client=client)

    with pytest.raises(StorageError) as exc_info:
        storage.get_private_bytes(key="uploads/quarantine/doc/test.pdf")

    assert exc_info.value.code == "STORAGE_DOWNLOAD_FAILED"


def test_put_failure_returns_stable_error() -> None:
    client = FakeS3Client()
    client.fail_put = True
    storage = S3ObjectStorage(_settings(), client=client)

    with pytest.raises(StorageError) as exc_info:
        storage.put_private_bytes(
            key="uploads/quarantine/doc/test.pdf",
            content=b"hello",
            content_type="application/pdf",
        )

    assert exc_info.value.code == "STORAGE_UPLOAD_FAILED"


def test_settings_reject_excessive_signed_url_ttl() -> None:
    with pytest.raises(ValueError, match="maximum allowed"):
        _settings(signed_url_ttl_seconds=MAX_SIGNED_URL_TTL_SECONDS + 1)


@pytest.mark.skipif(
    os.getenv("RUN_MINIO_TESTS") != "1",
    reason="MinIO integration tests require RUN_MINIO_TESTS=1",
)
def test_minio_round_trip_and_signed_url() -> None:
    storage = S3ObjectStorage(
        S3StorageSettings(
            endpoint=os.getenv("S3_ENDPOINT", "http://minio:9000"),
            region=os.getenv("S3_REGION", "us-east-1"),
            access_key=os.getenv("S3_ACCESS_KEY", "minioadmin"),
            secret_key=os.getenv("S3_SECRET_KEY", "minioadmin"),
            bucket=os.getenv("S3_BUCKET", "zayd-private"),
        )
    )
    key = f"test/{uuid.uuid4()}.txt"
    payload = b"minio-round-trip"

    storage.put_private_bytes(key=key, content=payload, content_type="text/plain")
    assert storage.get_private_bytes(key=key) == payload
    signed = storage.create_signed_get_url(
        key=key,
        filename="test.txt",
        content_type="text/plain",
    )

    request = Request(signed.url, method="GET")
    with urlopen(request, timeout=10) as response:
        assert response.status == 200
        assert response.read() == payload

    storage.delete_object(key=key)


def _settings(
    *,
    signed_url_ttl_seconds: int = DEFAULT_SIGNED_URL_TTL_SECONDS,
) -> S3StorageSettings:
    return S3StorageSettings(
        endpoint="http://minio:9000",
        region="us-east-1",
        access_key="minioadmin",
        secret_key="minioadmin",
        bucket="zayd-private",
        signed_url_ttl_seconds=signed_url_ttl_seconds,
    )
