# Agent Dropbox — Agent Instructions

## Shared Files

Your synced files from user devices are available at `/shared_data/`.

### Directory Structure

```
/shared_data/
  devices/{device_prefix}/{folder_name}/
    file1.txt
    subdir/
      file2.txt
```

Each device has a unique prefix (e.g., `devices/a1b2c3d4e5f6/`). Each sync folder appears as a subdirectory under that prefix.

### Rules

- You may **read** any file in `/shared_data/` freely.
- You may **create** new files in `/shared_data/` — they will sync to user devices on the next sync cycle (default: every 30 seconds).
- Do **not** delete or rename files in `/shared_data/` unless the user explicitly instructs you to.
- Do **not** modify files you did not create, unless instructed.
- Hidden files (names starting with `.`) are excluded from sync — do not rely on them for cross-device communication.

### File Size

- Files up to 100 MB sync normally.
- Files between 100 MB and 5 GB use multipart upload (handled automatically by the sync client).
- Files over 5 GB are skipped.

## General Behavior

- When a user asks you to work with their files, check `/shared_data/` first.
- If a file the user references is not in `/shared_data/`, let them know — it may not have synced yet or may be in a folder not registered for sync.
- Always confirm before performing destructive file operations (delete, overwrite, bulk rename).
