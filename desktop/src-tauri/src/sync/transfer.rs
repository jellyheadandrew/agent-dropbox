use std::path::Path;
use tokio::io::AsyncWriteExt;

pub async fn upload_file(presigned_url: &str, file_path: &Path) -> Result<(), String> {
    let data = tokio::fs::read(file_path)
        .await
        .map_err(|e| format!("Read error: {}", e))?;

    let client = reqwest::Client::new();
    let resp = client
        .put(presigned_url)
        .body(data)
        .send()
        .await
        .map_err(|e| format!("Upload error: {}", e))?;

    if !resp.status().is_success() {
        return Err(format!("Upload failed: HTTP {}", resp.status()));
    }

    Ok(())
}

pub async fn download_file(presigned_url: &str, file_path: &Path) -> Result<(), String> {
    if let Some(parent) = file_path.parent() {
        tokio::fs::create_dir_all(parent)
            .await
            .map_err(|e| format!("Mkdir error: {}", e))?;
    }

    let client = reqwest::Client::new();
    let resp = client
        .get(presigned_url)
        .send()
        .await
        .map_err(|e| format!("Download error: {}", e))?;

    if !resp.status().is_success() {
        return Err(format!("Download failed: HTTP {}", resp.status()));
    }

    let bytes = resp
        .bytes()
        .await
        .map_err(|e| format!("Read body error: {}", e))?;

    let mut file = tokio::fs::File::create(file_path)
        .await
        .map_err(|e| format!("Create file error: {}", e))?;

    file.write_all(&bytes)
        .await
        .map_err(|e| format!("Write error: {}", e))?;

    Ok(())
}

pub async fn delete_local_file(file_path: &Path) -> Result<(), String> {
    if file_path.exists() {
        tokio::fs::remove_file(file_path)
            .await
            .map_err(|e| format!("Delete error: {}", e))?;
    }
    Ok(())
}
