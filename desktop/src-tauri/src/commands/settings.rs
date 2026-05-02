use std::sync::Arc;
use tauri::State;
use tokio::sync::Mutex;

use crate::state::{AppSettings, AppState};

#[tauri::command]
pub async fn get_settings(
    state: State<'_, Arc<Mutex<AppState>>>,
) -> Result<AppSettings, String> {
    let app_state = state.lock().await;
    Ok(app_state.settings.clone())
}

#[tauri::command]
pub async fn update_settings(
    settings: AppSettings,
    state: State<'_, Arc<Mutex<AppState>>>,
) -> Result<(), String> {
    let mut app_state = state.lock().await;
    app_state.settings = settings;
    app_state.save();
    Ok(())
}
