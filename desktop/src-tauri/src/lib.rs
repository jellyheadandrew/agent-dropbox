mod auth;
mod commands;
mod config;
mod state;
mod sync;
mod tray;
mod watcher;

use std::sync::Arc;
use tauri::Manager;
use tokio::sync::Mutex;

pub fn run() {
    env_logger::init();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let app_state = Arc::new(Mutex::new(state::AppState::load()));
            app.manage(app_state.clone());

            tray::setup_tray(app)?;

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::auth::pair,
            commands::auth::check_auth,
            commands::auth::logout,
            commands::folders::add_folder,
            commands::folders::remove_folder,
            commands::folders::list_folders,
            commands::sync::trigger_sync,
            commands::sync::get_sync_status,
            commands::sync::resolve_conflict,
            commands::sync::get_conflicts,
            commands::settings::get_settings,
            commands::settings::update_settings,
        ])
        .run(tauri::generate_context!())
        .expect("error while running Agent Dropbox");
}
