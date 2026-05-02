import os
import secrets

# ── Auth ─────────────────────────────────────────────────────────────
SECRET_KEY: str = os.getenv("ADBOX_SECRET_KEY", secrets.token_hex(32))
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ADBOX_ACCESS_TOKEN_EXPIRE_MINUTES", "3600"))
REFRESH_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ADBOX_REFRESH_TOKEN_EXPIRE_MINUTES", "10080"))

# ── S3 ───────────────────────────────────────────────────────────────
S3_ENDPOINT_URL: str | None = os.getenv("ADBOX_S3_ENDPOINT_URL")  # None = default AWS
S3_ACCESS_KEY: str = os.getenv("ADBOX_S3_ACCESS_KEY", "")
S3_SECRET_KEY: str = os.getenv("ADBOX_S3_SECRET_KEY", "")
S3_REGION: str = os.getenv("ADBOX_S3_REGION", "us-east-1")
S3_BUCKET: str = os.getenv("ADBOX_S3_BUCKET", "agent-dropbox")
PRESIGNED_URL_EXPIRY: int = int(os.getenv("ADBOX_PRESIGNED_URL_EXPIRY", "3600"))

# ── Sync ─────────────────────────────────────────────────────────────
SYNC_FILE_SIZE_LIMIT: int = int(os.getenv("ADBOX_FILE_SIZE_LIMIT", str(5 * 1024 * 1024 * 1024)))  # 5 GB
MULTIPART_THRESHOLD: int = int(os.getenv("ADBOX_MULTIPART_THRESHOLD", str(100 * 1024 * 1024)))  # 100 MB
MULTIPART_PART_SIZE: int = int(os.getenv("ADBOX_MULTIPART_PART_SIZE", str(64 * 1024 * 1024)))  # 64 MB

# ── Database ─────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv("ADBOX_DATABASE_URL", "sqlite+aiosqlite:///./agent_dropbox.db")
