"""Thin boto3 wrapper for Cloudflare R2's S3 compatibility API.

This module only exposes read operations plus what uploading needs. There is
deliberately no delete or copy helper here: the app never removes or rewrites
objects other than through an upload the user explicitly confirmed.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator
from urllib.parse import unquote

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from .credentials import R2Credentials
from .keys import public_url


def endpoint_for(account_id: str, override: str = "") -> str:
    if override:
        return override.rstrip("/")
    return f"https://{account_id.strip().lower()}.r2.cloudflarestorage.com"


def make_client(creds: R2Credentials, endpoint_override: str = "", max_pool: int = 16):
    cfg = Config(
        region_name="auto",
        signature_version="s3v4",
        retries={"max_attempts": 3, "mode": "standard"},
        connect_timeout=20,
        read_timeout=300,
        max_pool_connections=max_pool,
        tcp_keepalive=True,
        # botocore >= 1.36 adds CRC32 trailers by default; R2 recommends turning
        # that off. Part integrity is checked with Content-MD5 instead.
        request_checksum_calculation="when_required",
        response_checksum_validation="when_required",
    )
    session = boto3.session.Session()
    return session.client(
        "s3",
        endpoint_url=endpoint_for(creds.account_id, endpoint_override),
        aws_access_key_id=creds.access_key_id,
        aws_secret_access_key=creds.secret_access_key,
        config=cfg,
    )


def error_code(exc: BaseException) -> str:
    if isinstance(exc, ClientError):
        err = exc.response.get("Error", {})
        code = str(err.get("Code", ""))
        if not code:
            status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            code = str(status or "")
        return code
    return type(exc).__name__


def http_status(exc: BaseException) -> int | None:
    if isinstance(exc, ClientError):
        return exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
    return None


def describe_error(exc: BaseException) -> str:
    code = error_code(exc)
    hints = {
        "InvalidAccessKeyId": "Access Key ID が正しくありません",
        "SignatureDoesNotMatch": "Secret Access Key が正しくありません",
        "AccessDenied": "権限がありません（APIトークンの権限・対象バケットを確認してください）",
        "NoSuchBucket": "バケットが見つかりません",
        "EndpointConnectionError": "R2 に接続できません（Account ID・ネットワークを確認してください）",
        "PreconditionFailed": "同じキーのファイルが既に存在するため書き込みを中止しました",
    }
    msg = hints.get(code)
    base = f"{code}: {exc}" if code else str(exc)
    return f"{msg}（{base}）" if msg else base


@dataclass
class ObjectInfo:
    key: str
    size: int
    etag: str
    last_modified: datetime | None
    metadata: dict | None = None
    content_type: str | None = None

    @property
    def is_multipart_etag(self) -> bool:
        return "-" in self.etag

    @property
    def md5_etag(self) -> str | None:
        return None if self.is_multipart_etag else self.etag.lower()

    @property
    def sha256(self) -> str | None:
        md = self.metadata or {}
        return (md.get("sha256") or "").lower() or None

    @property
    def source_sha256(self) -> str | None:
        md = self.metadata or {}
        return (md.get("source-sha256") or "").lower() or None

    @property
    def original_filename(self) -> str | None:
        md = self.metadata or {}
        v = md.get("original-filename")
        return unquote(v) if v else None


@dataclass
class UsageSummary:
    object_count: int
    total_bytes: int
    by_prefix: dict[str, tuple[int, int]]  # top-level folder → (count, bytes)
    listed_at: datetime


class R2Service:
    def __init__(self, client, bucket: str, public_base_url: str):
        self.client = client
        self.bucket = bucket
        self.public_base_url = public_base_url.rstrip("/")
        self._lock = threading.Lock()
        self.class_a_ops = 0
        self.class_b_ops = 0

    # Operation counters feed the monthly cost estimate.
    def count(self, kind: str, n: int = 1) -> None:
        with self._lock:
            if kind == "A":
                self.class_a_ops += n
            else:
                self.class_b_ops += n

    def public_url(self, key: str) -> str:
        return public_url(self.public_base_url, key)

    def test_connection(self) -> dict:
        self.client.head_bucket(Bucket=self.bucket)
        self.count("B")
        resp = self.client.list_objects_v2(Bucket=self.bucket, MaxKeys=1)
        self.count("A")
        return {"bucket": self.bucket, "sample": [o["Key"] for o in resp.get("Contents", [])]}

    def head(self, key: str) -> ObjectInfo | None:
        try:
            r = self.client.head_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            self.count("B")
            if http_status(exc) == 404 or error_code(exc) in ("404", "NoSuchKey", "NotFound"):
                return None
            raise
        self.count("B")
        return ObjectInfo(
            key=key,
            size=int(r.get("ContentLength", 0)),
            etag=str(r.get("ETag", "")).strip('"'),
            last_modified=r.get("LastModified"),
            metadata={k.lower(): v for k, v in (r.get("Metadata") or {}).items()},
            content_type=r.get("ContentType"),
        )

    def iter_objects(self, prefix: str = "") -> Iterator[ObjectInfo]:
        token = None
        while True:
            kwargs = {"Bucket": self.bucket, "MaxKeys": 1000}
            if prefix:
                kwargs["Prefix"] = prefix
            if token:
                kwargs["ContinuationToken"] = token
            resp = self.client.list_objects_v2(**kwargs)
            self.count("A")
            for o in resp.get("Contents", []):
                yield ObjectInfo(
                    key=o["Key"],
                    size=int(o.get("Size", 0)),
                    etag=str(o.get("ETag", "")).strip('"'),
                    last_modified=o.get("LastModified"),
                )
            if not resp.get("IsTruncated"):
                break
            token = resp.get("NextContinuationToken")
            if not token:
                break

    def list_all(self, prefix: str = "") -> list[ObjectInfo]:
        return list(self.iter_objects(prefix))

    @staticmethod
    def summarize(objects: list[ObjectInfo]) -> UsageSummary:
        by_prefix: dict[str, list[int]] = {}
        total = 0
        for o in objects:
            total += o.size
            top = o.key.split("/", 1)[0] + "/" if "/" in o.key else "（ルート）"
            slot = by_prefix.setdefault(top, [0, 0])
            slot[0] += 1
            slot[1] += o.size
        return UsageSummary(
            object_count=len(objects),
            total_bytes=total,
            by_prefix={k: (v[0], v[1]) for k, v in sorted(by_prefix.items(), key=lambda kv: -kv[1][1])},
            listed_at=datetime.now(),
        )
