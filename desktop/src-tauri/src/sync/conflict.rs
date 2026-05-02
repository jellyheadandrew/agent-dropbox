use crate::state::Conflict;

pub fn create_conflict(
    folder_name: &str,
    path: &str,
    local_size: u64,
    remote_size: u64,
    local_modified: Option<String>,
    remote_modified: Option<String>,
) -> Conflict {
    Conflict {
        id: uuid::Uuid::new_v4().to_string(),
        folder_name: folder_name.to_string(),
        path: path.to_string(),
        local_size,
        remote_size,
        local_modified,
        remote_modified,
    }
}
