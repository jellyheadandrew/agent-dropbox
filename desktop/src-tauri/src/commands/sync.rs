use std::sync::Arc;
use tauri::State;
use tokio::sync::Mutex;

use crate::state::{AppState, Conflict, ConflictResolution, FolderSyncStatus, SyncState};
use crate::sync::engine;

#[derive(serde::Serialize)]
pub struct SyncStatusResult {
    pub overall: SyncState,
    pub folders: std::collections::HashMap<String, FolderSyncStatus>,
}

#[tauri::command]
pub async fn trigger_sync(
    folder_name: Option<String>,
    state: State<'_, Arc<Mutex<AppState>>>,
) -> Result<(), String> {
    let app_state = state.lock().await;

    let server_url = app_state
        .auth
        .server_url
        .as_ref()
        .ok_or("Not authenticated")?
        .clone();
    let token = app_state
        .auth
        .access_token
        .as_ref()
        .ok_or("Not authenticated")?
        .clone();

    let folders: Vec<_> = if let Some(name) = &folder_name {
        app_state
            .sync_folders
            .iter()
            .filter(|f| &f.name == name)
            .cloned()
            .collect()
    } else {
        app_state.sync_folders.clone()
    };

    let settings = app_state.settings.clone();
    drop(app_state);

    for folder in folders {
        let state_clone = state.inner().clone();
        let server = server_url.clone();
        let tok = token.clone();
        let settings = settings.clone();

        tokio::spawn(async move {
            {
                let mut s = state_clone.lock().await;
                if let Some(status) = s.sync_status.get_mut(&folder.name) {
                    status.state = SyncState::Syncing;
                    status.error = None;
                }
            }

            let result = engine::sync_folder(&server, &tok, &folder, &settings).await;

            {
                let mut s = state_clone.lock().await;
                if let Some(status) = s.sync_status.get_mut(&folder.name) {
                    match result {
                        Ok(sync_result) => {
                            status.state = SyncState::Idle;
                            status.last_synced =
                                Some(chrono::Utc::now().to_rfc3339());
                            status.files_synced += sync_result.files_transferred;
                            s.conflicts.extend(sync_result.conflicts);
                        }
                        Err(e) => {
                            status.state = SyncState::Error;
                            status.error = Some(e);
                        }
                    }
                }
                s.save();
            }
        });
    }

    Ok(())
}

#[tauri::command]
pub async fn get_sync_status(
    state: State<'_, Arc<Mutex<AppState>>>,
) -> Result<SyncStatusResult, String> {
    let app_state = state.lock().await;

    let overall = if app_state
        .sync_status
        .values()
        .any(|s| s.state == SyncState::Error)
    {
        SyncState::Error
    } else if app_state
        .sync_status
        .values()
        .any(|s| s.state == SyncState::Syncing)
    {
        SyncState::Syncing
    } else {
        SyncState::Idle
    };

    Ok(SyncStatusResult {
        overall,
        folders: app_state.sync_status.clone(),
    })
}

#[tauri::command]
pub async fn get_conflicts(
    state: State<'_, Arc<Mutex<AppState>>>,
) -> Result<Vec<Conflict>, String> {
    let app_state = state.lock().await;
    Ok(app_state.conflicts.clone())
}

#[tauri::command]
pub async fn resolve_conflict(
    conflict_id: String,
    resolution: ConflictResolution,
    state: State<'_, Arc<Mutex<AppState>>>,
) -> Result<(), String> {
    let mut app_state = state.lock().await;

    let idx = app_state
        .conflicts
        .iter()
        .position(|c| c.id == conflict_id)
        .ok_or("Conflict not found")?;

    let conflict = app_state.conflicts.remove(idx);

    let server_url = app_state
        .auth
        .server_url
        .as_ref()
        .ok_or("Not authenticated")?
        .clone();
    let token = app_state
        .auth
        .access_token
        .as_ref()
        .ok_or("Not authenticated")?
        .clone();

    let folder = app_state
        .sync_folders
        .iter()
        .find(|f| f.name == conflict.folder_name)
        .ok_or("Folder not found")?
        .clone();

    drop(app_state);

    engine::resolve_single_conflict(&server_url, &token, &folder, &conflict, &resolution)
        .await
        .map_err(|e| format!("Failed to resolve conflict: {}", e))?;

    let mut app_state = state.lock().await;
    app_state.save();

    Ok(())
}
