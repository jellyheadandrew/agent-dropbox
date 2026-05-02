use std::path::PathBuf;
use std::sync::Arc;
use tauri::State;
use tokio::sync::Mutex;

use crate::state::{AppState, FolderSyncStatus, SyncFolderConfig, SyncState};

#[derive(serde::Deserialize)]
pub struct AddFolderArgs {
    pub name: String,
    pub path: String,
}

#[derive(serde::Serialize)]
pub struct FolderInfo {
    pub name: String,
    pub path: String,
    pub status: FolderSyncStatus,
}

#[tauri::command]
pub async fn add_folder(
    args: AddFolderArgs,
    state: State<'_, Arc<Mutex<AppState>>>,
) -> Result<FolderInfo, String> {
    let mut app_state = state.lock().await;

    if app_state.auth.access_token.is_none() {
        return Err("Not authenticated".into());
    }

    if app_state.sync_folders.iter().any(|f| f.name == args.name) {
        return Err(format!("Folder '{}' already exists", args.name));
    }

    let local_path = PathBuf::from(&args.path);
    if !local_path.exists() {
        return Err(format!("Path does not exist: {}", args.path));
    }
    if !local_path.is_dir() {
        return Err(format!("Path is not a directory: {}", args.path));
    }

    let server_url = app_state.auth.server_url.as_ref().ok_or("No server URL")?;
    let token = app_state.auth.access_token.as_ref().ok_or("No token")?;

    let client = reqwest::Client::new();
    let resp = client
        .post(format!("{}/folders", server_url))
        .bearer_auth(token)
        .json(&serde_json::json!({"folder_name": args.name}))
        .send()
        .await
        .map_err(|e| format!("Failed to register folder: {}", e))?;

    if !resp.status().is_success() {
        let body = resp.text().await.unwrap_or_default();
        return Err(format!("Server rejected folder: {}", body));
    }

    let folder = SyncFolderConfig {
        name: args.name.clone(),
        local_path,
    };

    let status = FolderSyncStatus {
        state: SyncState::Idle,
        last_synced: None,
        files_synced: 0,
        error: None,
    };

    app_state.sync_folders.push(folder);
    app_state
        .sync_status
        .insert(args.name.clone(), status.clone());
    app_state.save();

    Ok(FolderInfo {
        name: args.name,
        path: args.path,
        status,
    })
}

#[tauri::command]
pub async fn remove_folder(
    name: String,
    state: State<'_, Arc<Mutex<AppState>>>,
) -> Result<(), String> {
    let mut app_state = state.lock().await;

    let idx = app_state
        .sync_folders
        .iter()
        .position(|f| f.name == name)
        .ok_or(format!("Folder '{}' not found", name))?;

    if let (Some(server_url), Some(token)) = (
        app_state.auth.server_url.as_ref(),
        app_state.auth.access_token.as_ref(),
    ) {
        let client = reqwest::Client::new();
        let _ = client
            .delete(format!("{}/folders/{}", server_url, name))
            .bearer_auth(token)
            .send()
            .await;
    }

    app_state.sync_folders.remove(idx);
    app_state.sync_status.remove(&name);
    app_state.save();

    Ok(())
}

#[tauri::command]
pub async fn list_folders(
    state: State<'_, Arc<Mutex<AppState>>>,
) -> Result<Vec<FolderInfo>, String> {
    let app_state = state.lock().await;
    let folders = app_state
        .sync_folders
        .iter()
        .map(|f| {
            let status = app_state
                .sync_status
                .get(&f.name)
                .cloned()
                .unwrap_or(FolderSyncStatus {
                    state: SyncState::Idle,
                    last_synced: None,
                    files_synced: 0,
                    error: None,
                });
            FolderInfo {
                name: f.name.clone(),
                path: f.local_path.to_string_lossy().to_string(),
                status,
            }
        })
        .collect();
    Ok(folders)
}
