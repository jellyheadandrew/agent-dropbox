"""Local filesystem storage for Agent Dropbox.

Files are stored on the server's local disk. Upload/download URLs are
HMAC-signed and point back at the server itself, which proxies the
file transfers via streaming.
"""
import hashlib
import hmac
import math
import os
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlencode

from config import MULTIPART_PART_SIZE, URL_EXPIRY


class LocalStorage:

    def __init__(self, base_dir: str, server_base_url: str, secret_key: str):
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.server_base_url = server_base_url.rstrip("/")
        self.secret_key = secret_key
        self._multipart_dir = self.base_dir / ".multipart"
        self._multipart_dir.mkdir(exist_ok=True)

    # ── Path helpers ────────────────────────────────────────────────

    @staticmethod
    def device_prefix(s3_prefix: str, folder_name: str) -> str:
        return f"{s3_prefix}{folder_name}/"

    @staticmethod
    def is_hidden_path(rel_path: str) -> bool:
        return any(part.startswith(".") for part in rel_path.split("/") if part)

    def _resolve_key(self, key: str) -> Path:
        path = (self.base_dir / key).resolve()
        if not str(path).startswith(str(self.base_dir)):
            raise ValueError("Path traversal detected")
        return path

    # ── HMAC URL signing ────────────────────────────────────────────

    def _sign_url(self, action: str, key: str, expiry: int) -> str:
        expires = int(time.time()) + expiry
        message = f"{action}:{key}:{expires}"
        token = hmac.new(
            self.secret_key.encode(), message.encode(), hashlib.sha256
        ).hexdigest()
        encoded_key = quote(key, safe="/")
        params = urlencode({"token": token, "expires": str(expires)})
        return f"{self.server_base_url}/storage/files/{encoded_key}?{params}"

    def verify_signature(self, action: str, key: str, token: str, expires: str) -> bool:
        try:
            exp_int = int(expires)
        except ValueError:
            return False
        if time.time() > exp_int:
            return False
        message = f"{action}:{key}:{expires}"
        expected = hmac.new(
            self.secret_key.encode(), message.encode(), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(token, expected)

    # ── Object listing ──────────────────────────────────────────────

    def list_objects(self, prefix: str, skip_hidden: bool = False) -> list[dict]:
        target = self.base_dir / prefix
        if not target.exists():
            return []

        objects: list[dict] = []
        for path in target.rglob("*"):
            if not path.is_file():
                continue
            rel = str(path.relative_to(self.base_dir))
            rel_from_prefix = str(path.relative_to(target))
            if skip_hidden and self.is_hidden_path(rel_from_prefix):
                continue
            stat = path.stat()
            md5 = self._compute_md5(path)
            objects.append({
                "key": rel,
                "etag": md5,
                "size": stat.st_size,
                "last_modified": datetime.fromtimestamp(
                    stat.st_mtime, tz=timezone.utc
                ).isoformat(),
            })
        return objects

    @staticmethod
    def _compute_md5(path: Path) -> str:
        h = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    # ── Head / existence ────────────────────────────────────────────

    def head_object(self, key: str) -> dict | None:
        path = self._resolve_key(key)
        if not path.exists() or not path.is_file():
            return None
        stat = path.stat()
        return {
            "key": key,
            "etag": self._compute_md5(path),
            "size": stat.st_size,
            "last_modified": datetime.fromtimestamp(
                stat.st_mtime, tz=timezone.utc
            ).isoformat(),
        }

    # ── URL generation ──────────────────────────────────────────────

    def generate_upload_url(self, key: str, expiry: int = URL_EXPIRY) -> str:
        return self._sign_url("PUT", key, expiry)

    def generate_download_url(self, key: str, expiry: int = URL_EXPIRY) -> str:
        return self._sign_url("GET", key, expiry)

    # ── Delete ──────────────────────────────────────────────────────

    def delete_object(self, key: str) -> None:
        path = self._resolve_key(key)
        if path.exists():
            path.unlink()
            self._cleanup_empty_parents(path)

    def delete_objects(self, keys: list[str]) -> dict:
        deleted = []
        errors = []
        for key in keys:
            try:
                self.delete_object(key)
                deleted.append({"Key": key})
            except Exception as e:
                errors.append({"Key": key, "Message": str(e)})
        return {"Deleted": deleted, "Errors": errors}

    def _cleanup_empty_parents(self, path: Path) -> None:
        parent = path.parent
        while parent != self.base_dir and parent.exists():
            try:
                next(parent.iterdir())
                break
            except StopIteration:
                parent.rmdir()
                parent = parent.parent

    # ── File I/O (used by the proxy router) ─────────────────────────

    def get_file_path(self, key: str) -> Path:
        return self._resolve_key(key)

    def write_file(self, key: str, data: bytes) -> dict:
        path = self._resolve_key(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        stat = path.stat()
        return {"etag": self._compute_md5(path), "size": stat.st_size}

    # ── Multipart upload ────────────────────────────────────────────

    def initiate_multipart_upload(self, key: str) -> str:
        upload_id = uuid.uuid4().hex
        parts_dir = self._multipart_dir / upload_id
        parts_dir.mkdir(parents=True, exist_ok=True)
        meta_file = parts_dir / ".meta"
        meta_file.write_text(key)
        return upload_id

    def generate_part_upload_url(
        self, key: str, upload_id: str, part_number: int, expiry: int = URL_EXPIRY,
    ) -> str:
        expires = int(time.time()) + expiry
        message = f"PART:{upload_id}:{part_number}:{expires}"
        token = hmac.new(
            self.secret_key.encode(), message.encode(), hashlib.sha256
        ).hexdigest()
        encoded_key = quote(key, safe="/")
        params = urlencode({
            "token": token,
            "expires": str(expires),
            "upload_id": upload_id,
            "part_number": str(part_number),
        })
        return f"{self.server_base_url}/storage/files/{encoded_key}/parts?{params}"

    def verify_part_signature(
        self, upload_id: str, part_number: int, token: str, expires: str,
    ) -> bool:
        try:
            exp_int = int(expires)
        except ValueError:
            return False
        if time.time() > exp_int:
            return False
        message = f"PART:{upload_id}:{part_number}:{expires}"
        expected = hmac.new(
            self.secret_key.encode(), message.encode(), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(token, expected)

    def write_part(self, upload_id: str, part_number: int, data: bytes) -> str:
        parts_dir = self._multipart_dir / upload_id
        if not parts_dir.exists():
            raise ValueError("Invalid upload_id")
        part_path = parts_dir / f"part_{part_number:05d}"
        part_path.write_bytes(data)
        return hashlib.md5(data).hexdigest()

    def complete_multipart_upload(
        self, key: str, upload_id: str, parts: list[dict],
    ) -> dict:
        parts_dir = self._multipart_dir / upload_id
        if not parts_dir.exists():
            raise ValueError("Invalid upload_id")

        dest = self._resolve_key(key)
        dest.parent.mkdir(parents=True, exist_ok=True)

        sorted_parts = sorted(parts, key=lambda p: p["PartNumber"])
        with open(dest, "wb") as out:
            for part in sorted_parts:
                part_path = parts_dir / f"part_{part['PartNumber']:05d}"
                if not part_path.exists():
                    raise ValueError(f"Missing part {part['PartNumber']}")
                with open(part_path, "rb") as inp:
                    shutil.copyfileobj(inp, out)

        shutil.rmtree(parts_dir, ignore_errors=True)
        return {"ETag": self._compute_md5(dest)}

    def abort_multipart_upload(self, key: str, upload_id: str) -> None:
        parts_dir = self._multipart_dir / upload_id
        if parts_dir.exists():
            shutil.rmtree(parts_dir, ignore_errors=True)

    def compute_part_count(self, file_size: int) -> int:
        return math.ceil(file_size / MULTIPART_PART_SIZE)
