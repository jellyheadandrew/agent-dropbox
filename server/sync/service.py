"""Sync service: remote scanning, URL generation, and server-side deletes.

Uses LocalStorage for all file operations — files stored on the server's
local disk, transfers proxied through HMAC-signed URLs.
"""
from datetime import datetime, timezone

from config import MULTIPART_PART_SIZE, MULTIPART_THRESHOLD, URL_EXPIRY, SYNC_FILE_SIZE_LIMIT
from storage import LocalStorage
from sync.schemas import (
    MultipartCompleteRequest,
    MultipartCompleteResponse,
    MultipartInitRequest,
    MultipartInitResponse,
    MultipartPartInfo,
    SyncResolveDeleteError,
    SyncResolveDeleteResult,
    SyncResolveRequest,
    SyncResolveResponse,
    SyncResolveUrlEntry,
    SyncScanRequest,
    SyncScanResponse,
    SyncScannedFile,
    SyncSkippedFile,
    SyncVerifyRequest,
    SyncVerifyResponse,
    SyncVerifyResult,
)


class SyncService:

    def __init__(self, storage: LocalStorage):
        self.storage = storage

    def scan_remote(self, request: SyncScanRequest, s3_prefix: str) -> SyncScanResponse:
        prefix = self.storage.device_prefix(s3_prefix, request.folder_name)
        remote_objects = self.storage.list_objects(prefix, skip_hidden=True)

        files: list[SyncScannedFile] = []
        skipped: list[SyncSkippedFile] = []

        for obj in remote_objects:
            rel_path = obj["key"][len(prefix):]
            if not rel_path or rel_path.endswith("/"):
                continue
            if self.storage.is_hidden_path(rel_path):
                skipped.append(SyncSkippedFile(path=rel_path, size=obj["size"], reason="hidden"))
                continue
            if obj["size"] > SYNC_FILE_SIZE_LIMIT:
                skipped.append(SyncSkippedFile(path=rel_path, size=obj["size"], reason="exceeds_size_limit"))
            else:
                files.append(SyncScannedFile(path=rel_path, size=obj["size"], etag=obj["etag"]))

        scanned_at = datetime.now(timezone.utc).isoformat()
        return SyncScanResponse(files=files, skipped=skipped, scanned_at=scanned_at)

    def resolve_sync(self, request: SyncResolveRequest, s3_prefix: str) -> SyncResolveResponse:
        prefix = self.storage.device_prefix(s3_prefix, request.folder_name)

        upload_urls: list[SyncResolveUrlEntry] = []
        for entry in request.uploads:
            full_key = prefix + entry.path
            if entry.size > MULTIPART_THRESHOLD:
                url = ""
            else:
                url = self.storage.generate_upload_url(full_key)
            upload_urls.append(SyncResolveUrlEntry(
                path=entry.path, url=url, method="PUT", expires_in=URL_EXPIRY,
            ))

        download_urls: list[SyncResolveUrlEntry] = []
        for entry in request.downloads:
            full_key = prefix + entry.path
            url = self.storage.generate_download_url(full_key)
            download_urls.append(SyncResolveUrlEntry(
                path=entry.path, url=url, method="GET", expires_in=URL_EXPIRY,
            ))

        deleted: list[SyncResolveDeleteResult] = []
        delete_errors: list[SyncResolveDeleteError] = []
        for entry in request.deletes:
            full_key = prefix + entry.path
            try:
                self.storage.delete_object(full_key)
                deleted.append(SyncResolveDeleteResult(path=entry.path, status="deleted"))
            except Exception as exc:
                delete_errors.append(SyncResolveDeleteError(path=entry.path, error=str(exc)))

        return SyncResolveResponse(
            upload_urls=upload_urls,
            download_urls=download_urls,
            deleted=deleted,
            delete_errors=delete_errors,
        )

    def verify_files(self, request: SyncVerifyRequest, s3_prefix: str) -> SyncVerifyResponse:
        prefix = self.storage.device_prefix(s3_prefix, request.folder_name)
        remote_objects = self.storage.list_objects(prefix, skip_hidden=True)

        remote_map: dict[str, int] = {}
        for obj in remote_objects:
            rel_path = obj["key"][len(prefix):]
            if rel_path and not rel_path.endswith("/") and not self.storage.is_hidden_path(rel_path):
                remote_map[rel_path] = obj["size"]

        results = [SyncVerifyResult(path=p, size=remote_map.get(p, 0)) for p in request.paths]
        return SyncVerifyResponse(results=results)

    def init_multipart(self, request: MultipartInitRequest, s3_prefix: str) -> MultipartInitResponse:
        prefix = self.storage.device_prefix(s3_prefix, request.folder_name)
        full_key = prefix + request.path

        upload_id = self.storage.initiate_multipart_upload(full_key)
        part_count = self.storage.compute_part_count(request.file_size)

        parts = [
            MultipartPartInfo(
                part_number=i,
                url=self.storage.generate_part_upload_url(full_key, upload_id, i),
            )
            for i in range(1, part_count + 1)
        ]

        return MultipartInitResponse(
            upload_id=upload_id, key=full_key, parts=parts, part_size=MULTIPART_PART_SIZE,
        )

    def complete_multipart(self, request: MultipartCompleteRequest, s3_prefix: str) -> MultipartCompleteResponse:
        expected_prefix = self.storage.device_prefix(s3_prefix, request.folder_name)
        if not request.key.startswith(expected_prefix):
            raise ValueError("Key does not belong to this device's folder")

        parts = [
            {"PartNumber": p.part_number, "ETag": p.etag}
            for p in sorted(request.parts, key=lambda x: x.part_number)
        ]

        result = self.storage.complete_multipart_upload(request.key, request.upload_id, parts)
        return MultipartCompleteResponse(
            key=request.key, etag=result.get("ETag", "").strip('"'),
        )
