#!/usr/bin/env python3
"""Generate a pairing token for a new device.

Usage:
    python generate-token.py --device-name "My Laptop"
    python generate-token.py --device-name "Work Desktop" --db ../server/agent_dropbox.db
    python generate-token.py --device-name "Phone" --env-file /path/to/.env
"""
import argparse
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "server"))

from auth.token import generate_pairing_token, generate_s3_prefix, hash_token


def load_env_file(env_path: str) -> None:
    path = Path(env_path)
    if not path.exists():
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key not in os.environ:
                os.environ[key] = value


def main():
    parser = argparse.ArgumentParser(description="Generate Agent Dropbox pairing token")
    parser.add_argument("--device-name", required=True, help="Human-readable device name")
    parser.add_argument("--db", default=None, help="Path to SQLite database file")
    parser.add_argument("--env-file", default=None, help="Path to .env file (auto-detected if not specified)")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    install_dir = script_dir.parent

    if args.env_file:
        load_env_file(args.env_file)
    else:
        for candidate in [
            install_dir / ".env",
            install_dir / "server" / ".env",
            Path.home() / "agent-dropbox" / ".env",
        ]:
            if candidate.exists():
                load_env_file(str(candidate))
                break

    db_path = Path(args.db) if args.db else install_dir / "agent_dropbox.db"
    if not db_path.exists():
        server_db = install_dir / "server" / "agent_dropbox.db"
        if server_db.exists():
            db_path = server_db

    if not db_path.exists():
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_name TEXT NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                s3_prefix TEXT NOT NULL UNIQUE,
                created_at TEXT DEFAULT (datetime('now')),
                last_seen_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                folder_name TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(user_id, folder_name)
            )
        """)
        conn.commit()
    else:
        conn = sqlite3.connect(str(db_path))

    token = generate_pairing_token()
    hashed = hash_token(token)
    s3_prefix = generate_s3_prefix()

    conn.execute(
        "INSERT INTO users (device_name, token_hash, s3_prefix) VALUES (?, ?, ?)",
        (args.device_name, hashed, s3_prefix),
    )
    conn.commit()
    conn.close()

    print(f"\n  Device:  {args.device_name}")
    print(f"  Token:   {token}")
    print(f"  Prefix:  {s3_prefix}")
    print(f"\n  Enter this token in the Agent Dropbox desktop app to pair.\n")


if __name__ == "__main__":
    main()
