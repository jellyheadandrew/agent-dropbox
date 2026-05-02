use std::collections::HashSet;

use super::manifest::{FileEntry, Manifest};

#[derive(Debug, Clone)]
pub enum SyncAction {
    Upload(String),
    Download(String),
    DeleteRemote(String),
    DeleteLocal(String),
    Conflict(String),
}

/// Three-way diff: compare Local (L), Remote (R), and Snapshot (S).
///
/// L = current local files
/// R = remote S3 files (from /sync/scan)
/// S = snapshot from last successful sync
pub fn three_way_diff(
    local: &Manifest,
    remote: &Manifest,
    snapshot: &Manifest,
) -> Vec<SyncAction> {
    let mut actions = Vec::new();

    let all_paths: HashSet<&String> = local
        .keys()
        .chain(remote.keys())
        .chain(snapshot.keys())
        .collect();

    for path in all_paths {
        let l = local.get(path);
        let r = remote.get(path);
        let s = snapshot.get(path);

        match (l, r, s) {
            // Case 1: Only in local (new local file)
            (Some(_), None, None) => {
                actions.push(SyncAction::Upload(path.clone()));
            }

            // Case 2: Only in remote (new remote file)
            (None, Some(_), None) => {
                actions.push(SyncAction::Download(path.clone()));
            }

            // Case 3: In local + snapshot, not in remote (remotely deleted)
            (Some(l_entry), None, Some(s_entry)) => {
                if entries_equal(l_entry, s_entry) {
                    actions.push(SyncAction::DeleteLocal(path.clone()));
                } else {
                    actions.push(SyncAction::Conflict(path.clone()));
                }
            }

            // Case 4: In remote + snapshot, not in local (locally deleted)
            (None, Some(r_entry), Some(s_entry)) => {
                if entries_equal_by_size(r_entry, s_entry) {
                    actions.push(SyncAction::DeleteRemote(path.clone()));
                } else {
                    actions.push(SyncAction::Conflict(path.clone()));
                }
            }

            // Case 5: In all three
            (Some(l_entry), Some(r_entry), Some(s_entry)) => {
                let l_changed = !entries_equal(l_entry, s_entry);
                let r_changed = !entries_equal_by_size(r_entry, s_entry);

                if !l_changed && !r_changed {
                    // No changes
                } else if l_changed && !r_changed {
                    actions.push(SyncAction::Upload(path.clone()));
                } else if !l_changed && r_changed {
                    actions.push(SyncAction::Download(path.clone()));
                } else {
                    // Both changed
                    if l_entry.md5 == r_entry.md5 {
                        // Same change on both sides
                    } else {
                        actions.push(SyncAction::Conflict(path.clone()));
                    }
                }
            }

            // Case 6: In local + remote, not in snapshot (both added)
            (Some(l_entry), Some(r_entry), None) => {
                if l_entry.md5 == r_entry.md5 {
                    // Same file, just add to snapshot
                } else {
                    actions.push(SyncAction::Conflict(path.clone()));
                }
            }

            // Case 7: Only in snapshot (both deleted)
            (None, None, Some(_)) => {
                // Remove from snapshot, no action needed
            }

            // Impossible: nothing anywhere
            (None, None, None) => {}
        }
    }

    actions
}

fn entries_equal(a: &FileEntry, b: &FileEntry) -> bool {
    a.md5 == b.md5 && a.size == b.size
}

fn entries_equal_by_size(remote: &FileEntry, snapshot: &FileEntry) -> bool {
    remote.md5 == snapshot.md5
        || (remote.size == snapshot.size && remote.md5.is_empty())
}
