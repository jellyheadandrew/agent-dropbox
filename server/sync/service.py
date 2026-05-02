"""Sync service: S3 scanning, presigned URL generation, and server-side deletes.

Adapted from ARI's SyncService, stripped of all Kubernetes dependencies.
"""
from datetime import datetime, timezone

from config import MULTIPART_PART_SIZE, MULTIPART_THRESHOLD, PRESIGNED_URL_EXPIRY, SYNC_FILE_SIZE_LIMIT
from s3 import client as s3_client
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

    @staticmethod
    def scan_remote(request: SyncScanRequest, s3_prefix: str) -> SyncScanResponse:
        prefix = s3_client.device_prefix(s3_prefix, request.folder_name)
        remote_objects = s3_client.list_objects(prefix, skip_hidden=True)

        files: list[SyncScannedFile] = []
        skipped: list[SyncSkippedFile] = []

        for obj in remote_objects:
            rel_path = obj["key"][len(prefix):]
            if not rel_path or rel_path.endswith("/"):
                continue
            if s3_client.is_hidden_path(rel_path):
                skipped.append(SyncSkippedFile(path=rel_path, size=obj["size"], reason="hidden"))
                continue
            if obj["size"] > SYNC_FILE_SIZE_LIMIT:
                skipped.append(SyncSkippedFile(path=rel_path, size=obj["size"], reason="exceeds_size_limit"))
            else:
                files.append(SyncScannedFile(path=rel_path, size=obj["size"], etag=obj["etag"]))

        scanned_at = datetime.now(timezone.utc).isoformat()
        return SyncScanResponse(files=files, skipped=skipped, scanned_at=scanned_at)

    @staticmethod
    def resolve_sync(request: SyncResolveRequest, s3_prefix: str) -> SyncResolveResponse:
        prefix = s3_client.device_prefix(s3_prefix, request.folder_name)

        upload_urls: list[SyncResolveUrlEntry] = []
        for entry in request.uploads:
            full_key = prefix + entry.path
            if entry.size > MULTIPART_THRESHOLD:
                url = ""
            else:
                url = s3_client.generate_presigned_put(full_key)
            upload_urls.append(SyncResolveUrlEntry(
                path=entry.path, url=url, method="PUT", expires_in=PRESIGNED_URL_EXPIRY,
            ))

        download_urls: list[SyncResolveUrlEntry] = []
        for entry in request.downloads:
            full_key = prefix + entry.path
            url = s3_client.generate_presigned_get(full_key)
            download_urls.append(SyncResolveUrlEntry(
                path=entry.path, url=url, method="GET", expires_in=PRESIGNED_URL_EXPIRY,
            ))

        deleted: list[SyncResolveDeleteResult] = []
        delete_errors: list[SyncResolveDeleteError] = []
        for entry in request.deletes:
            full_key = prefix + entry.path
            try:
                s3_client.delete_object(full_key)
                deleted.append(SyncResolveDeleteResult(path=entry.path, status="deleted"))
            except Exception as exc:
                delete_errors.append(SyncResolveDeleteError(path=entry.path, error=str(exc)))

        return SyncResolveResponse(
            upload_urls=upload_urls,
            download_urls=download_urls,
            deleted=deleted,
            delete_errors=delete_errors,
        )

    @staticmethod
    def verify_files(request: SyncVerifyRequest, s3_prefix: str) -> SyncVerifyResponse:
        prefix = s3_client.device_prefix(s3_prefix, request.folder_name)
        remote_objects = s3_client.list_objects(prefix, skip_hidden=True)

        remote_map: dict[str, int] = {}
        for obj in remote_objects:
            rel_path = obj["key"][len(prefix):]
            if rel_path and not rel_path.endswith("/") and not s3_client.is_hidden_path(rel_path):
                remote_map[rel_path] = obj["size"]

        results = [SyncVerifyResult(path=p, size=remote_map.get(p, 0)) for p in request.paths]
        return SyncVerifyResponse(results=results)

    @staticmethod
    def init_multipart(request: MultipartInitRequest, s3_prefix: str) -> MultipartInitResponse:
        prefix = s3_client.device_prefix(s3_prefix, request.folder_name)
        full_key = prefix + request.path

        upload_id = s3_client.initiate_multipart_upload(full_key)
        part_count = s3_client.compute_part_count(request.file_size)

        parts = [
            MultipartPartInfo(
                part_number=i,
                url=s3_client.generate_presigned_upload_part(full_key, upload_id, i),
            )
            for i in range(1, part_count + 1)
        ]

        return MultipartInitResponse(
            upload_id=upload_id, key=full_key, parts=parts, part_size=MULTIPART_PART_SIZE,
        )

    @staticmethod
    def complete_multipart(request: MultipartCompleteRequest, s3_prefix: str) -> MultipartCompleteResponse:
        expected_prefix = s3_client.device_prefix(s3_prefix, request.folder_name)
        if not request.key.startswith(expected_prefix):
            raise ValueError("Key does not belong to this device's folder")

        parts = [
            {"PartNumber": p.part_number, "ETag": p.etag}
            for p in sorted(request.parts, key=lambda x: x.part_number)
        ]

        result = s3_client.complete_multipart_upload(request.key, request.upload_id, parts)
        return MultipartCompleteResponse(
            key=request.key, etag=result.get("ETag", "").strip('"'),
        )
