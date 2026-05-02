use std::sync::Arc;
use tauri::State;
use tokio::sync::Mutex;

use crate::state::{AppState, AuthState};

#[derive(serde::Deserialize)]
pub struct PairArgs {
    pub server_url: String,
    pub token: String,
}

#[derive(serde::Serialize)]
pub struct PairResult {
    pub device_name: String,
}

#[derive(serde::Serialize)]
pub struct AuthStatusResult {
    pub logged_in: bool,
    pub server_url: Option<String>,
    pub device_name: Option<String>,
}

#[tauri::command]
pub async fn pair(
    args: PairArgs,
    state: State<'_, Arc<Mutex<AppState>>>,
) -> Result<PairResult, String> {
    let server_url = args.server_url.trim_end_matches('/').to_string();
    let client = reqwest::Client::new();

    let resp = client
        .post(format!("{}/auth/pair", server_url))
        .json(&serde_json::json!({"token": args.token}))
        .send()
        .await
        .map_err(|e| format!("Connection failed: {}", e))?;

    if !resp.status().is_success() {
        let status = resp.status();
        let body = resp.text().await.unwrap_or_default();
        return Err(format!("Pairing failed ({}): {}", status, body));
    }

    let body: serde_json::Value = resp
        .json()
        .await
        .map_err(|e| format!("Invalid response: {}", e))?;

    let access_token = body["access_token"]
        .as_str()
        .ok_or("Missing access_token")?
        .to_string();
    let refresh_token = body["refresh_token"]
        .as_str()
        .ok_or("Missing refresh_token")?
        .to_string();
    let device_name = body["device_name"]
        .as_str()
        .ok_or("Missing device_name")?
        .to_string();

    let mut app_state = state.lock().await;
    app_state.auth = AuthState {
        server_url: Some(server_url),
        access_token: Some(access_token),
        refresh_token: Some(refresh_token),
        device_name: Some(device_name.clone()),
    };
    app_state.save();

    Ok(PairResult { device_name })
}

#[tauri::command]
pub async fn check_auth(state: State<'_, Arc<Mutex<AppState>>>) -> Result<AuthStatusResult, String> {
    let app_state = state.lock().await;
    Ok(AuthStatusResult {
        logged_in: app_state.auth.access_token.is_some(),
        server_url: app_state.auth.server_url.clone(),
        device_name: app_state.auth.device_name.clone(),
    })
}

#[tauri::command]
pub async fn logout(state: State<'_, Arc<Mutex<AppState>>>) -> Result<(), String> {
    let mut app_state = state.lock().await;
    app_state.auth = AuthState {
        server_url: None,
        access_token: None,
        refresh_token: None,
        device_name: None,
    };
    app_state.sync_folders.clear();
    app_state.sync_status.clear();
    app_state.conflicts.clear();
    app_state.save();
    Ok(())
}
