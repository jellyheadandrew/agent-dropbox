# Agent Memory

## Environment

- Shared files from user devices are synced to the `/shared_data/` directory.
- Files are synced via Agent Dropbox, a bidirectional file sync system.
- Directory convention: `devices/{device_prefix}/{folder_name}/{file_path}` — each registered device has a unique prefix.
- Changes I make to files in `/shared_data/` will sync back to user devices within approximately 30 seconds.
- Hidden files (names starting with `.`) are excluded from sync.
- I should not delete or rename files in `/shared_data/` without explicit user instruction.
- Files over 5 GB are not synced. Files over 100 MB use multipart upload.
