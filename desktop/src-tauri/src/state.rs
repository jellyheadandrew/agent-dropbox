use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppState {
    pub auth: AuthState,
    pub sync_folders: Vec<SyncFolderConfig>,
    pub sync_status: HashMap<String, FolderSyncStatus>,
    pub settings: AppSettings,
    pub conflicts: Vec<Conflict>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuthState {
    pub server_url: Option<String>,
    pub access_token: Option<String>,
    pub refresh_token: Option<String>,
    pub device_name: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncFolderConfig {
    pub name: String,
    pub local_path: PathBuf,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FolderSyncStatus {
    pub state: SyncState,
    pub last_synced: Option<String>,
    pub files_synced: u64,
    pub error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum SyncState {
    Idle,
    Syncing,
    Error,
    Paused,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppSettings {
    pub sync_interval_secs: u64,
    pub auto_sync: bool,
    pub launch_on_startup: bool,
    pub ignore_patterns: Vec<String>,
    pub max_concurrent_transfers: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Conflict {
    pub id: String,
    pub folder_name: String,
    pub path: String,
    pub local_size: u64,
    pub remote_size: u64,
    pub local_modified: Option<String>,
    pub remote_modified: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ConflictResolution {
    KeepLocal,
    KeepRemote,
    KeepBoth,
}

impl AppState {
    pub fn load() -> Self {
        let config_path = Self::config_path();
        if config_path.exists() {
            if let Ok(data) = std::fs::read_to_string(&config_path) {
                if let Ok(state) = serde_json::from_str(&data) {
                    return state;
                }
            }
        }
        Self::default()
    }

    pub fn save(&self) {
        let config_path = Self::config_path();
        if let Some(parent) = config_path.parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        if let Ok(data) = serde_json::to_string_pretty(self) {
            let _ = std::fs::write(&config_path, data);
        }
    }

    fn config_path() -> PathBuf {
        dirs::config_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join("agent-dropbox")
            .join("config.json")
    }
}

impl Default for AppState {
    fn default() -> Self {
        Self {
            auth: AuthState {
                server_url: None,
                access_token: None,
                refresh_token: None,
                device_name: None,
            },
            sync_folders: Vec::new(),
            sync_status: HashMap::new(),
            settings: AppSettings {
                sync_interval_secs: 30,
                auto_sync: true,
                launch_on_startup: false,
                ignore_patterns: vec![
                    "*.tmp".into(),
                    "*.swp".into(),
                    "~$*".into(),
                    ".DS_Store".into(),
                    "Thumbs.db".into(),
                    "desktop.ini".into(),
                ],
                max_concurrent_transfers: 4,
            },
            conflicts: Vec::new(),
        }
    }
}
