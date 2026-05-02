from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.deps import get_current_user
from auth.token import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_s3_prefix,
    hash_token,
    verify_token,
)
from database import get_db
from models import SyncFolder, User
from sync.schemas import (
    AuthStatus,
    FolderCreate,
    FolderResponse,
    MultipartCompleteRequest,
    MultipartCompleteResponse,
    MultipartInitRequest,
    MultipartInitResponse,
    PairRequest,
    PairResponse,
    RefreshRequest,
    RefreshResponse,
    SyncResolveRequest,
    SyncResolveResponse,
    SyncScanRequest,
    SyncScanResponse,
    SyncVerifyRequest,
    SyncVerifyResponse,
)
from sync.service import SyncService

# ── Auth Router ──────────────────────────────────────────────────────

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/pair", response_model=PairResponse)
async def pair_device(req: PairRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()

    for user in users:
        if verify_token(req.token, user.token_hash):
            access = create_access_token(user.id, user.s3_prefix)
            refresh = create_refresh_token(user.id, user.s3_prefix)
            return PairResponse(
                access_token=access,
                refresh_token=refresh,
                device_name=user.device_name,
            )

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid pairing token")


@auth_router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(req.refresh_token, expected_type="refresh")
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    access = create_access_token(user.id, user.s3_prefix)
    return RefreshResponse(access_token=access)


@auth_router.get("/me", response_model=AuthStatus)
async def auth_me(user: User = Depends(get_current_user)):
    return AuthStatus(user_id=user.id, device_name=user.device_name, s3_prefix=user.s3_prefix)


# ── Folders Router ───────────────────────────────────────────────────

folders_router = APIRouter(prefix="/folders", tags=["folders"])


@folders_router.get("", response_model=list[FolderResponse])
async def list_folders(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SyncFolder).where(SyncFolder.user_id == user.id))
    folders = result.scalars().all()
    return [FolderResponse(id=f.id, folder_name=f.folder_name) for f in folders]


@folders_router.post("", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    req: FolderCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(SyncFolder).where(SyncFolder.user_id == user.id, SyncFolder.folder_name == req.folder_name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Folder already registered")

    folder = SyncFolder(user_id=user.id, folder_name=req.folder_name)
    db.add(folder)
    await db.commit()
    await db.refresh(folder)
    return FolderResponse(id=folder.id, folder_name=folder.folder_name)


@folders_router.delete("/{folder_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(
    folder_name: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SyncFolder).where(SyncFolder.user_id == user.id, SyncFolder.folder_name == folder_name)
    )
    folder = result.scalar_one_or_none()
    if folder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    await db.delete(folder)
    await db.commit()


# ── Sync Router ──────────────────────────────────────────────────────

sync_router = APIRouter(prefix="/sync", tags=["sync"])


@sync_router.post("/scan", response_model=SyncScanResponse)
async def sync_scan(req: SyncScanRequest, user: User = Depends(get_current_user)):
    return SyncService.scan_remote(req, user.s3_prefix)


@sync_router.post("/resolve", response_model=SyncResolveResponse)
async def sync_resolve(req: SyncResolveRequest, user: User = Depends(get_current_user)):
    return SyncService.resolve_sync(req, user.s3_prefix)


@sync_router.post("/verify", response_model=SyncVerifyResponse)
async def sync_verify(req: SyncVerifyRequest, user: User = Depends(get_current_user)):
    return SyncService.verify_files(req, user.s3_prefix)


@sync_router.post("/multipart/init", response_model=MultipartInitResponse)
async def multipart_init(req: MultipartInitRequest, user: User = Depends(get_current_user)):
    return SyncService.init_multipart(req, user.s3_prefix)


@sync_router.post("/multipart/complete", response_model=MultipartCompleteResponse)
async def multipart_complete(req: MultipartCompleteRequest, user: User = Depends(get_current_user)):
    try:
        return SyncService.complete_multipart(req, user.s3_prefix)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
