from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import SECRET_KEY, SERVER_BASE_URL, STORAGE_DIR
from database import init_db
from storage import LocalStorage
from storage.router import set_storage, storage_router
from sync.router import auth_router, folders_router, set_sync_service, sync_router
from sync.service import SyncService


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    storage = LocalStorage(
        base_dir=STORAGE_DIR,
        server_base_url=SERVER_BASE_URL,
        secret_key=SECRET_KEY,
    )
    set_storage(storage)
    set_sync_service(SyncService(storage))
    yield


app = FastAPI(
    title="Agent Dropbox Sync Server",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(folders_router)
app.include_router(sync_router)
app.include_router(storage_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
