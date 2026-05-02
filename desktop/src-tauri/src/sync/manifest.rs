use md5::{Digest, Md5};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::io::Read;
use std::path::Path;
use walkdir::WalkDir;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileEntry {
    pub size: u64,
    pub md5: String,
    pub mtime: Option<String>,
}

pub type Manifest = HashMap<String, FileEntry>;

pub fn build_local_manifest(root: &Path, ignore_patterns: &[String]) -> Result<Manifest, String> {
    let mut manifest = HashMap::new();

    for entry in WalkDir::new(root).follow_links(false).into_iter().filter_map(|e| e.ok()) {
        if !entry.file_type().is_file() {
            continue;
        }

        let full_path = entry.path();
        let rel_path = full_path
            .strip_prefix(root)
            .map_err(|e| e.to_string())?
            .to_string_lossy()
            .replace('\\', "/");

        if rel_path.is_empty() {
            continue;
        }

        if should_ignore(&rel_path, ignore_patterns) {
            continue;
        }

        if is_hidden_path(&rel_path) {
            continue;
        }

        let metadata = std::fs::metadata(full_path).map_err(|e| format!("{}: {}", rel_path, e))?;
        let size = metadata.len();

        let md5 = compute_md5(full_path).map_err(|e| format!("{}: {}", rel_path, e))?;

        let mtime = metadata
            .modified()
            .ok()
            .and_then(|t| {
                chrono::DateTime::<chrono::Utc>::from(t)
                    .to_rfc3339()
                    .into()
            });

        manifest.insert(
            rel_path,
            FileEntry { size, md5, mtime },
        );
    }

    Ok(manifest)
}

fn compute_md5(path: &Path) -> Result<String, String> {
    let mut file = std::fs::File::open(path).map_err(|e| e.to_string())?;
    let mut hasher = Md5::new();
    let mut buffer = [0u8; 81920];

    loop {
        let n = file.read(&mut buffer).map_err(|e| e.to_string())?;
        if n == 0 {
            break;
        }
        hasher.update(&buffer[..n]);
    }

    Ok(format!("{:x}", hasher.finalize()))
}

fn is_hidden_path(rel_path: &str) -> bool {
    rel_path.split('/').any(|seg| !seg.is_empty() && seg.starts_with('.'))
}

fn should_ignore(rel_path: &str, patterns: &[String]) -> bool {
    let filename = rel_path.rsplit('/').next().unwrap_or(rel_path);
    for pattern in patterns {
        if matches_glob(filename, pattern) {
            return true;
        }
    }
    false
}

fn matches_glob(name: &str, pattern: &str) -> bool {
    if pattern.starts_with('*') {
        let suffix = &pattern[1..];
        name.ends_with(suffix)
    } else if pattern.ends_with('*') {
        let prefix = &pattern[..pattern.len() - 1];
        name.starts_with(prefix)
    } else {
        name == pattern
    }
}
