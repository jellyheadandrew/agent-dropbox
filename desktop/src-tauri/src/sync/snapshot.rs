use std::path::PathBuf;

use super::manifest::Manifest;
use crate::config;

pub fn load_snapshot(folder_name: &str) -> Manifest {
    let path = snapshot_path(folder_name);
    if path.exists() {
        if let Ok(data) = std::fs::read_to_string(&path) {
            if let Ok(manifest) = serde_json::from_str(&data) {
                return manifest;
            }
        }
    }
    Manifest::new()
}

pub fn save_snapshot(folder_name: &str, manifest: &Manifest) -> Result<(), String> {
    let path = snapshot_path(folder_name);
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let data = serde_json::to_string(manifest).map_err(|e| e.to_string())?;
    std::fs::write(&path, data).map_err(|e| e.to_string())?;
    Ok(())
}

fn snapshot_path(folder_name: &str) -> PathBuf {
    config::snapshots_dir().join(format!("{}.json", folder_name))
}
