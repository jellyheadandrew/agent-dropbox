import { invoke } from "@tauri-apps/api/core";
import type {
  AppSettings,
  AuthStatus,
  Conflict,
  FolderInfo,
  SyncStatusResult,
} from "./types";

export async function pair(
  serverUrl: string,
  token: string
): Promise<{ device_name: string }> {
  return invoke("pair", { args: { server_url: serverUrl, token } });
}

export async function checkAuth(): Promise<AuthStatus> {
  return invoke("check_auth");
}

export async function logout(): Promise<void> {
  return invoke("logout");
}

export async function addFolder(
  name: string,
  path: string
): Promise<FolderInfo> {
  return invoke("add_folder", { args: { name, path } });
}

export async function removeFolder(name: string): Promise<void> {
  return invoke("remove_folder", { name });
}

export async function listFolders(): Promise<FolderInfo[]> {
  return invoke("list_folders");
}

export async function triggerSync(folderName?: string): Promise<void> {
  return invoke("trigger_sync", { folderName: folderName ?? null });
}

export async function getSyncStatus(): Promise<SyncStatusResult> {
  return invoke("get_sync_status");
}

export async function getConflicts(): Promise<Conflict[]> {
  return invoke("get_conflicts");
}

export async function resolveConflict(
  conflictId: string,
  resolution: "KeepLocal" | "KeepRemote" | "KeepBoth"
): Promise<void> {
  return invoke("resolve_conflict", {
    conflictId,
    resolution,
  });
}

export async function getSettings(): Promise<AppSettings> {
  return invoke("get_settings");
}

export async function updateSettings(settings: AppSettings): Promise<void> {
  return invoke("update_settings", { settings });
}
