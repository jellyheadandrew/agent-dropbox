export interface AuthStatus {
  logged_in: boolean;
  server_url: string | null;
  device_name: string | null;
}

export interface FolderInfo {
  name: string;
  path: string;
  status: FolderSyncStatus;
}

export interface FolderSyncStatus {
  state: "Idle" | "Syncing" | "Error" | "Paused";
  last_synced: string | null;
  files_synced: number;
  error: string | null;
}

export interface SyncStatusResult {
  overall: "Idle" | "Syncing" | "Error" | "Paused";
  folders: Record<string, FolderSyncStatus>;
}

export interface Conflict {
  id: string;
  folder_name: string;
  path: string;
  local_size: number;
  remote_size: number;
  local_modified: string | null;
  remote_modified: string | null;
}

export interface AppSettings {
  sync_interval_secs: number;
  auto_sync: boolean;
  launch_on_startup: boolean;
  ignore_patterns: string[];
  max_concurrent_transfers: number;
}
