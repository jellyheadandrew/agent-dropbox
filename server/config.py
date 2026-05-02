import os
import secrets

# ── Auth ─────────────────────────────────────────────────────────────
SECRET_KEY: str = os.getenv("ADBOX_SECRET_KEY", secrets.token_hex(32))
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ADBOX_ACCESS_TOKEN_EXPIRE_MINUTES", "3600"))
REFRESH_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ADBOX_REFRESH_TOKEN_EXPIRE_MINUTES", "10080"))

# ── Storage ──────────────────────────────────────────────────────────
STORAGE_DIR: str = os.getenv("ADBOX_STORAGE_DIR", "./storage_data")
SERVER_BASE_URL: str = os.getenv("ADBOX_SERVER_BASE_URL", "http://localhost:8000")
URL_EXPIRY: int = int(os.getenv("ADBOX_URL_EXPIRY", "3600"))

# ── Sync ─────────────────────────────────────────────────────────────
SYNC_FILE_SIZE_LIMIT: int = int(os.getenv("ADBOX_FILE_SIZE_LIMIT", str(5 * 1024 * 1024 * 1024)))  # 5 GB
MULTIPART_THRESHOLD: int = int(os.getenv("ADBOX_MULTIPART_THRESHOLD", str(100 * 1024 * 1024)))  # 100 MB
MULTIPART_PART_SIZE: int = int(os.getenv("ADBOX_MULTIPART_PART_SIZE", str(64 * 1024 * 1024)))  # 64 MB

# ── Database ─────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv("ADBOX_DATABASE_URL", "sqlite+aiosqlite:///./agent_dropbox.db")
