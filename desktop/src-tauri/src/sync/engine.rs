use std::collections::HashMap;

use crate::state::{AppSettings, Conflict, ConflictResolution, SyncFolderConfig};

use super::conflict::create_conflict;
use super::diff::{three_way_diff, SyncAction};
use super::manifest::{build_local_manifest, FileEntry, Manifest};
use super::snapshot::{load_snapshot, save_snapshot};
use super::transfer;

pub struct SyncResult {
    pub files_transferred: u64,
    pub conflicts: Vec<Conflict>,
}

pub async fn sync_folder(
    server_url: &str,
    token: &str,
    folder: &SyncFolderConfig,
    settings: &AppSettings,
) -> Result<SyncResult, String> {
    // 1. Build local manifest
    let local = build_local_manifest(&folder.local_path, &settings.ignore_patterns)?;

    // 2. Scan remote
    let remote = scan_remote(server_url, token, &folder.name).await?;

    // 3. Load snapshot
    let snapshot = load_snapshot(&folder.name);

    // 4. Compute 3-way diff
    let actions = three_way_diff(&local, &remote, &snapshot);

    // 5. Separate actions
    let mut uploads: Vec<String> = Vec::new();
    let mut downloads: Vec<String> = Vec::new();
    let mut remote_deletes: Vec<String> = Vec::new();
    let mut local_deletes: Vec<String> = Vec::new();
    let mut conflicts: Vec<Conflict> = Vec::new();

    for action in &actions {
        match action {
            SyncAction::Upload(p) => uploads.push(p.clone()),
            SyncAction::Download(p) => downloads.push(p.clone()),
            SyncAction::DeleteRemote(p) => remote_deletes.push(p.clone()),
            SyncAction::DeleteLocal(p) => local_deletes.push(p.clone()),
            SyncAction::Conflict(p) => {
                let l = local.get(p);
                let r = remote.get(p);
                conflicts.push(create_conflict(
                    &folder.name,
                    p,
                    l.map(|e| e.size).unwrap_or(0),
                    r.map(|e| e.size).unwrap_or(0),
                    l.and_then(|e| e.mtime.clone()),
                    r.and_then(|e| e.mtime.clone()),
                ));
            }
        }
    }

    // 6. Resolve presigned URLs
    let resolve = resolve_sync(
        server_url,
        token,
        &folder.name,
        &uploads,
        &local,
        &downloads,
        &remote_deletes,
    )
    .await?;

    let mut files_transferred: u64 = 0;

    // 7. Execute uploads
    for url_entry in &resolve.upload_urls {
        if url_entry.url.is_empty() {
            continue; // multipart needed
        }
        let file_path = folder.local_path.join(&url_entry.path);
        if let Err(e) = transfer::upload_file(&url_entry.url, &file_path).await {
            log::error!("Upload failed for {}: {}", url_entry.path, e);
            continue;
        }
        files_transferred += 1;
    }

    // 8. Execute downloads
    for url_entry in &resolve.download_urls {
        let file_path = folder.local_path.join(&url_entry.path);
        if let Err(e) = transfer::download_file(&url_entry.url, &file_path).await {
            log::error!("Download failed for {}: {}", url_entry.path, e);
            continue;
        }
        files_transferred += 1;
    }

    // 9. Execute local deletes
    for path in &local_deletes {
        let file_path = folder.local_path.join(path);
        let _ = transfer::delete_local_file(&file_path).await;
    }

    // 10. Build new snapshot from current state
    let mut new_snapshot = build_local_manifest(&folder.local_path, &settings.ignore_patterns)?;
    // Include remote-only files that were successfully downloaded
    for (path, entry) in &remote {
        if !new_snapshot.contains_key(path) && !remote_deletes.contains(path) {
            new_snapshot.insert(path.clone(), entry.clone());
        }
    }
    save_snapshot(&folder.name, &new_snapshot)?;

    Ok(SyncResult {
        files_transferred,
        conflicts,
    })
}

pub async fn resolve_single_conflict(
    server_url: &str,
    token: &str,
    folder: &SyncFolderConfig,
    conflict: &Conflict,
    resolution: &ConflictResolution,
) -> Result<(), String> {
    match resolution {
        ConflictResolution::KeepLocal => {
            let resolve = resolve_sync(
                server_url,
                token,
                &folder.name,
                &[conflict.path.clone()],
                &{
                    let mut m = Manifest::new();
                    m.insert(
                        conflict.path.clone(),
                        FileEntry {
                            size: conflict.local_size,
                            md5: String::new(),
                            mtime: conflict.local_modified.clone(),
                        },
                    );
                    m
                },
                &[],
                &[],
            )
            .await?;

            for url_entry in &resolve.upload_urls {
                if !url_entry.url.is_empty() {
                    let file_path = folder.local_path.join(&url_entry.path);
                    transfer::upload_file(&url_entry.url, &file_path).await?;
                }
            }
        }
        ConflictResolution::KeepRemote => {
            let resolve = resolve_sync(
                server_url,
                token,
                &folder.name,
                &[],
                &Manifest::new(),
                &[conflict.path.clone()],
                &[],
            )
            .await?;

            for url_entry in &resolve.download_urls {
                let file_path = folder.local_path.join(&url_entry.path);
                transfer::download_file(&url_entry.url, &file_path).await?;
            }
        }
        ConflictResolution::KeepBoth => {
            // Rename local file with .conflict suffix
            let file_path = folder.local_path.join(&conflict.path);
            if file_path.exists() {
                let timestamp = chrono::Utc::now().format("%Y%m%d-%H%M%S");
                let stem = file_path
                    .file_stem()
                    .map(|s| s.to_string_lossy().to_string())
                    .unwrap_or_default();
                let ext = file_path
                    .extension()
                    .map(|s| format!(".{}", s.to_string_lossy()))
                    .unwrap_or_default();
                let conflict_name = format!("{}.conflict-{}{}", stem, timestamp, ext);
                let conflict_path = file_path.with_file_name(conflict_name);
                tokio::fs::rename(&file_path, &conflict_path)
                    .await
                    .map_err(|e| e.to_string())?;
            }

            // Download remote version
            let resolve = resolve_sync(
                server_url,
                token,
                &folder.name,
                &[],
                &Manifest::new(),
                &[conflict.path.clone()],
                &[],
            )
            .await?;

            for url_entry in &resolve.download_urls {
                let file_path = folder.local_path.join(&url_entry.path);
                transfer::download_file(&url_entry.url, &file_path).await?;
            }
        }
    }

    Ok(())
}

// ── Server API calls ────────────────────────────────────────────────

#[derive(serde::Deserialize)]
struct ScanResponse {
    files: Vec<ScannedFile>,
}

#[derive(serde::Deserialize)]
struct ScannedFile {
    path: String,
    size: u64,
    etag: String,
}

async fn scan_remote(
    server_url: &str,
    token: &str,
    folder_name: &str,
) -> Result<Manifest, String> {
    let client = reqwest::Client::new();
    let resp = client
        .post(format!("{}/sync/scan", server_url))
        .bearer_auth(token)
        .json(&serde_json::json!({"folder_name": folder_name}))
        .send()
        .await
        .map_err(|e| format!("Scan failed: {}", e))?;

    if !resp.status().is_success() {
        return Err(format!("Scan failed: HTTP {}", resp.status()));
    }

    let body: ScanResponse = resp.json().await.map_err(|e| format!("Parse error: {}", e))?;

    let mut manifest = Manifest::new();
    for file in body.files {
        manifest.insert(
            file.path,
            FileEntry {
                size: file.size,
                md5: file.etag,
                mtime: None,
            },
        );
    }

    Ok(manifest)
}

#[derive(serde::Deserialize)]
struct ResolveResponse {
    upload_urls: Vec<UrlEntry>,
    download_urls: Vec<UrlEntry>,
}

#[derive(serde::Deserialize, Clone)]
struct UrlEntry {
    path: String,
    url: String,
}

async fn resolve_sync(
    server_url: &str,
    token: &str,
    folder_name: &str,
    upload_paths: &[String],
    local_manifest: &Manifest,
    download_paths: &[String],
    delete_paths: &[String],
) -> Result<ResolveResponse, String> {
    let uploads: Vec<serde_json::Value> = upload_paths
        .iter()
        .map(|p| {
            let size = local_manifest.get(p).map(|e| e.size).unwrap_or(0);
            serde_json::json!({"path": p, "size": size})
        })
        .collect();

    let downloads: Vec<serde_json::Value> = download_paths
        .iter()
        .map(|p| serde_json::json!({"path": p}))
        .collect();

    let deletes: Vec<serde_json::Value> = delete_paths
        .iter()
        .map(|p| serde_json::json!({"path": p}))
        .collect();

    let client = reqwest::Client::new();
    let resp = client
        .post(format!("{}/sync/resolve", server_url))
        .bearer_auth(token)
        .json(&serde_json::json!({
            "folder_name": folder_name,
            "uploads": uploads,
            "downloads": downloads,
            "deletes": deletes,
        }))
        .send()
        .await
        .map_err(|e| format!("Resolve failed: {}", e))?;

    if !resp.status().is_success() {
        return Err(format!("Resolve failed: HTTP {}", resp.status()));
    }

    resp.json()
        .await
        .map_err(|e| format!("Parse error: {}", e))
}
