from pydantic import BaseModel, Field, field_validator


def _check_sync_path(path: str) -> None:
    if ".." in path or path.startswith("/"):
        raise ValueError(f"Invalid path: '{path}' — must be relative without '..'")
    if "\x00" in path:
        raise ValueError(f"Null byte in path: '{path}'")
    if any(seg.startswith(".") for seg in path.split("/") if seg):
        raise ValueError(f"Hidden path not allowed: '{path}'")


# ── Auth ─────────────────────────────────────────────────────────────

class PairRequest(BaseModel):
    token: str = Field(..., min_length=1)


class PairResponse(BaseModel):
    access_token: str
    refresh_token: str
    device_name: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthStatus(BaseModel):
    user_id: int
    device_name: str
    s3_prefix: str


# ── Folders ──────────────────────────────────────────────────────────

class FolderCreate(BaseModel):
    folder_name: str = Field(..., min_length=1, max_length=255, pattern=r"^[a-zA-Z0-9_\-. ]+$")


class FolderResponse(BaseModel):
    id: int
    folder_name: str


# ── Sync Scan ────────────────────────────────────────────────────────

class SyncScanRequest(BaseModel):
    folder_name: str = Field(..., min_length=1, max_length=255)


class SyncScannedFile(BaseModel):
    path: str
    size: int
    etag: str


class SyncSkippedFile(BaseModel):
    path: str
    size: int
    reason: str


class SyncScanResponse(BaseModel):
    files: list[SyncScannedFile] = Field(default_factory=list)
    skipped: list[SyncSkippedFile] = Field(default_factory=list)
    scanned_at: str


# ── Sync Resolve ─────────────────────────────────────────────────────

class SyncResolveUploadEntry(BaseModel):
    path: str = Field(..., min_length=1, max_length=4096)
    size: int = Field(..., ge=0)


class SyncResolveDownloadEntry(BaseModel):
    path: str = Field(..., min_length=1, max_length=4096)


class SyncResolveDeleteEntry(BaseModel):
    path: str = Field(..., min_length=1, max_length=4096)


class SyncResolveRequest(BaseModel):
    folder_name: str = Field(..., min_length=1, max_length=255)
    uploads: list[SyncResolveUploadEntry] = Field(default_factory=list)
    downloads: list[SyncResolveDownloadEntry] = Field(default_factory=list)
    deletes: list[SyncResolveDeleteEntry] = Field(default_factory=list)

    @field_validator("uploads")
    @classmethod
    def validate_uploads(cls, v: list[SyncResolveUploadEntry]) -> list[SyncResolveUploadEntry]:
        if len(v) > 10_000:
            raise ValueError("Too many uploads (max 10,000)")
        for entry in v:
            _check_sync_path(entry.path)
        return v

    @field_validator("downloads")
    @classmethod
    def validate_downloads(cls, v: list[SyncResolveDownloadEntry]) -> list[SyncResolveDownloadEntry]:
        if len(v) > 10_000:
            raise ValueError("Too many downloads (max 10,000)")
        for entry in v:
            _check_sync_path(entry.path)
        return v

    @field_validator("deletes")
    @classmethod
    def validate_deletes(cls, v: list[SyncResolveDeleteEntry]) -> list[SyncResolveDeleteEntry]:
        if len(v) > 10_000:
            raise ValueError("Too many deletes (max 10,000)")
        for entry in v:
            _check_sync_path(entry.path)
        return v


class SyncResolveUrlEntry(BaseModel):
    path: str
    url: str
    method: str
    expires_in: int


class SyncResolveDeleteResult(BaseModel):
    path: str
    status: str


class SyncResolveDeleteError(BaseModel):
    path: str
    error: str


class SyncResolveResponse(BaseModel):
    upload_urls: list[SyncResolveUrlEntry] = Field(default_factory=list)
    download_urls: list[SyncResolveUrlEntry] = Field(default_factory=list)
    deleted: list[SyncResolveDeleteResult] = Field(default_factory=list)
    delete_errors: list[SyncResolveDeleteError] = Field(default_factory=list)


# ── Sync Verify ──────────────────────────────────────────────────────

class SyncVerifyRequest(BaseModel):
    folder_name: str = Field(..., min_length=1, max_length=255)
    paths: list[str] = Field(..., min_length=1)

    @field_validator("paths")
    @classmethod
    def validate_paths(cls, v: list[str]) -> list[str]:
        if len(v) > 1_000:
            raise ValueError("Too many paths (max 1,000)")
        for p in v:
            _check_sync_path(p)
        return v


class SyncVerifyResult(BaseModel):
    path: str
    size: int


class SyncVerifyResponse(BaseModel):
    results: list[SyncVerifyResult]


# ── Multipart ────────────────────────────────────────────────────────

class MultipartInitRequest(BaseModel):
    folder_name: str = Field(..., min_length=1, max_length=255)
    path: str = Field(..., min_length=1, max_length=4096)
    file_size: int = Field(..., gt=0)

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        _check_sync_path(v)
        return v


class MultipartPartInfo(BaseModel):
    part_number: int
    url: str


class MultipartInitResponse(BaseModel):
    upload_id: str
    key: str
    parts: list[MultipartPartInfo]
    part_size: int


class MultipartCompletePartEntry(BaseModel):
    part_number: int = Field(..., ge=1)
    etag: str = Field(..., min_length=1)


class MultipartCompleteRequest(BaseModel):
    folder_name: str = Field(..., min_length=1, max_length=255)
    key: str = Field(..., min_length=1)
    upload_id: str = Field(..., min_length=1)
    parts: list[MultipartCompletePartEntry] = Field(..., min_length=1)


class MultipartCompleteResponse(BaseModel):
    key: str
    etag: str
