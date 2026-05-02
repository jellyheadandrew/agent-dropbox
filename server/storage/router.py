"""File transfer proxy endpoints for local storage.

Handles HMAC-signed upload/download requests. All file data is
streamed to avoid loading large files into memory.
"""
from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse, StreamingResponse

from config import SYNC_FILE_SIZE_LIMIT

storage_router = APIRouter(prefix="/storage", tags=["storage"])

_storage = None


def set_storage(storage):
    global _storage
    _storage = storage


def _get_storage():
    if _storage is None:
        raise HTTPException(status_code=500, detail="Storage not initialized")
    return _storage


@storage_router.get("/files/{key:path}")
async def download_file(
    key: str,
    token: str = Query(...),
    expires: str = Query(...),
):
    store = _get_storage()
    if not store.verify_signature("GET", key, token, expires):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or expired signature")

    file_path = store.get_file_path(key)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    return FileResponse(
        path=str(file_path),
        media_type="application/octet-stream",
        filename=file_path.name,
    )


@storage_router.put("/files/{key:path}")
async def upload_file(
    key: str,
    request: Request,
    token: str = Query(...),
    expires: str = Query(...),
):
    store = _get_storage()
    if not store.verify_signature("PUT", key, token, expires):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or expired signature")

    body = await request.body()
    if len(body) > SYNC_FILE_SIZE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds size limit ({SYNC_FILE_SIZE_LIMIT} bytes)",
        )

    result = store.write_file(key, body)
    return {"etag": result["etag"], "size": result["size"]}


@storage_router.put("/files/{key:path}/parts")
async def upload_part(
    key: str,
    request: Request,
    token: str = Query(...),
    expires: str = Query(...),
    upload_id: str = Query(...),
    part_number: str = Query(...),
):
    store = _get_storage()

    try:
        pn = int(part_number)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid part_number")

    if not store.verify_part_signature(upload_id, pn, token, expires):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or expired signature")

    body = await request.body()
    etag = store.write_part(upload_id, pn, body)
    return {"etag": etag, "part_number": pn}
