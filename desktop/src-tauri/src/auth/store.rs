use keyring::Entry;

const SERVICE_NAME: &str = "agent-dropbox";

pub fn save_token(key: &str, value: &str) -> Result<(), String> {
    let entry = Entry::new(SERVICE_NAME, key).map_err(|e| e.to_string())?;
    entry.set_password(value).map_err(|e| e.to_string())
}

pub fn get_token(key: &str) -> Option<String> {
    let entry = Entry::new(SERVICE_NAME, key).ok()?;
    entry.get_password().ok()
}

pub fn delete_token(key: &str) -> Result<(), String> {
    let entry = Entry::new(SERVICE_NAME, key).map_err(|e| e.to_string())?;
    entry.delete_credential().map_err(|e| e.to_string())
}
