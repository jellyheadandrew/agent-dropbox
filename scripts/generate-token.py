#!/usr/bin/env python3
"""Generate a pairing token for a new device.

Usage:
    python generate-token.py --device-name "My Laptop"
    python generate-token.py --device-name "Work Desktop" --db ../server/agent_dropbox.db
"""
import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "server"))

from auth.token import generate_pairing_token, generate_s3_prefix, hash_token


def main():
    parser = argparse.ArgumentParser(description="Generate Agent Dropbox pairing token")
    parser.add_argument("--device-name", required=True, help="Human-readable device name")
    parser.add_argument("--db", default="agent_dropbox.db", help="Path to SQLite database file")
    args = parser.parse_args()

    db_path = Path(args.db)
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
