"""S3-compatible object storage abstractions and adapters."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Literal, Protocol
from urllib.parse import urlparse

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

StorageOperation = Literal["put", "get", "delete", "presign_get"]
StorageUrlMethod = Literal["GET"]
S3_ADDRESSING_STYLE = Literal["auto", "path", "virtual"]

DEFAULT_SIGNED_URL_TTL_SECONDS = 300
MAX_SIGNED_URL_TTL_SECONDS = 900


@dataclass(frozen=True)
class StorageObjectRef:
    bucket: str
    key: str


@dataclass(frozen=True)
class SignedUrl:
    method: StorageUrlMethod
    url: str
    expires_at: int
    expires_in_seconds: int


@dataclass(frozen=True)
class StoredObject:
    object_ref: StorageObjectRef
    signed_get_url: SignedUrl


class StorageError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        operation: StorageOperation,
        status_code: int = 502,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.operation = operation
        self.status_code = status_code


class ObjectStorage(Protocol):
    def put_private_bytes(
        self,
        *,
        key: str,
        content: bytes,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> StorageObjectRef: ...

    def get_private_bytes(self, *, key: str) -> bytes: ...

    def delete_object(self, *, key: str) -> None: ...

    def create_signed_get_url(
        self,
        *,
        key: str,
        filename: str,
        content_type: str,
        expires_in_seconds: int = DEFAULT_SIGNED_URL_TTL_SECONDS,
    ) -> SignedUrl: ...


@dataclass(frozen=True)
class S3StorageSettings:
    endpoint: str
    region: str
    access_key: str
    secret_key: str
    bucket: str
    addressing_style: S3_ADDRESSING_STYLE = "auto"
    max_attempts: int = 3
    signed_url_ttl_seconds: int = DEFAULT_SIGNED_URL_TTL_SECONDS

    def __post_init__(self) -> None:
        if self.addressing_style not in {"auto", "path", "virtual"}:
            raise ValueError("S3 addressing style must be auto, path, or virtual.")
        if self.max_attempts < 1:
            raise ValueError("S3 max attempts must be at least 1.")
        if self.signed_url_ttl_seconds < 1:
            raise ValueError("S3 signed URL TTL must be positive.")
        if self.signed_url_ttl_seconds > MAX_SIGNED_URL_TTL_SECONDS:
            raise ValueError("S3 signed URL TTL exceeds the maximum allowed value.")

    @property
    def use_path_style(self) -> bool:
        if self.addressing_style == "path":
            return True
        if self.addressing_style == "virtual":
            return False
        hostname = urlparse(self.endpoint).hostname or ""
        return hostname in {"localhost", "127.0.0.1", "::1", "minio"}


class S3ObjectStorage:
    def __init__(self, settings: S3StorageSettings, *, client: BaseClient | None = None) -> None:
        self.settings = settings
        self._client = client or self._build_client(settings)

    def put_private_bytes(
        self,
        *,
        key: str,
        content: bytes,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> StorageObjectRef:
        try:
            self._client.put_object(
                Bucket=self.settings.bucket,
                Key=key,
                Body=content,
                ContentType=content_type,
                Metadata=metadata or {},
            )
        except (ClientError, BotoCoreError) as exc:
            raise StorageError(
                "STORAGE_UPLOAD_FAILED",
                "Object storage upload failed.",
                operation="put",
            ) from exc
        return StorageObjectRef(bucket=self.settings.bucket, key=key)

    def get_private_bytes(self, *, key: str) -> bytes:
        try:
            response = self._client.get_object(Bucket=self.settings.bucket, Key=key)
            body = response["Body"]
            try:
                data: bytes = body.read()
                return data
            finally:
                body.close()
        except (ClientError, BotoCoreError) as exc:
            raise StorageError(
                "STORAGE_DOWNLOAD_FAILED",
                "Object storage download failed.",
                operation="get",
            ) from exc

    def delete_object(self, *, key: str) -> None:
        try:
            self._client.delete_object(Bucket=self.settings.bucket, Key=key)
        except (ClientError, BotoCoreError) as exc:
            raise StorageError(
                "STORAGE_DELETE_FAILED",
                "Object storage delete failed.",
                operation="delete",
            ) from exc

    def create_signed_get_url(
        self,
        *,
        key: str,
        filename: str,
        content_type: str,
        expires_in_seconds: int = DEFAULT_SIGNED_URL_TTL_SECONDS,
    ) -> SignedUrl:
        ttl = min(expires_in_seconds, self.settings.signed_url_ttl_seconds)
        if ttl < 1:
            ttl = 1
        try:
            url = self._client.generate_presigned_url(
                ClientMethod="get_object",
                Params={
                    "Bucket": self.settings.bucket,
                    "Key": key,
                    "ResponseContentType": content_type,
                    "ResponseContentDisposition": _content_disposition(filename),
                },
                ExpiresIn=ttl,
            )
        except (ClientError, BotoCoreError) as exc:
            raise StorageError(
                "STORAGE_SIGNED_URL_FAILED",
                "Object storage signed URL generation failed.",
                operation="presign_get",
            ) from exc
        return SignedUrl(
            method="GET",
            url=url,
            expires_at=int(time.time()) + ttl,
            expires_in_seconds=ttl,
        )

    @staticmethod
    def _build_client(settings: S3StorageSettings) -> BaseClient:
        return boto3.client(
            "s3",
            endpoint_url=settings.endpoint,
            region_name=settings.region,
            aws_access_key_id=settings.access_key,
            aws_secret_access_key=settings.secret_key,
            config=Config(
                signature_version="s3v4",
                retries={"max_attempts": settings.max_attempts, "mode": "standard"},
                s3={"addressing_style": "path" if settings.use_path_style else "virtual"},
            ),
        )


def storage_settings_from_env() -> S3StorageSettings:
    return S3StorageSettings(
        endpoint=os.getenv("S3_ENDPOINT", "http://minio:9000").strip(),
        region=os.getenv("S3_REGION", "us-east-1").strip(),
        access_key=os.getenv("S3_ACCESS_KEY", "minioadmin").strip(),
        secret_key=os.getenv("S3_SECRET_KEY", "minioadmin").strip(),
        bucket=os.getenv("S3_BUCKET", "zayd-private").strip(),
        addressing_style=os.getenv("S3_ADDRESSING_STYLE", "auto").strip().lower(),  # type: ignore[arg-type]
        max_attempts=int(os.getenv("S3_MAX_ATTEMPTS", "3").strip()),
        signed_url_ttl_seconds=int(
            os.getenv("S3_SIGNED_URL_TTL_SECONDS", str(DEFAULT_SIGNED_URL_TTL_SECONDS)).strip()
        ),
    )


def _content_disposition(filename: str) -> str:
    return f'attachment; filename="{filename.replace(chr(34), "")}"'
