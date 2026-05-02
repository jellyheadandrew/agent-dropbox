import { removeFolder } from "../lib/tauri";
import type { FolderInfo, SyncStatusResult } from "../lib/types";

interface Props {
  folders: FolderInfo[];
  status: SyncStatusResult | null;
  onRefresh: () => void;
}

export default function FolderList({ folders, status, onRefresh }: Props) {
  const handleRemove = async (name: string) => {
    await removeFolder(name);
    onRefresh();
  };

  if (folders.length === 0) {
    return (
      <div className="folder-list" style={{ textAlign: "center", padding: "40px 0", color: "var(--text-dim)" }}>
        No folders synced yet. Click "Add Folder" to get started.
      </div>
    );
  }

  return (
    <div className="folder-list">
      {folders.map((folder) => {
        const folderStatus = status?.folders[folder.name] ?? folder.status;
        const stateClass = folderStatus.state.toLowerCase();

        return (
          <div key={folder.name} className="folder-item">
            <div className="name">
              <span>
                <span className={`status-dot ${stateClass}`} />
                {folder.name}
              </span>
              <button
                className="secondary"
                style={{ padding: "2px 8px", fontSize: "11px" }}
                onClick={() => handleRemove(folder.name)}
              >
                Remove
              </button>
            </div>
            <div className="path">{folder.path}</div>
            <div className="meta">
              <span>{folderStatus.files_synced} files synced</span>
              <span>
                {folderStatus.last_synced
                  ? `Last: ${new Date(folderStatus.last_synced).toLocaleTimeString()}`
                  : "Never synced"}
              </span>
            </div>
            {folderStatus.error && (
              <div className="error-text" style={{ marginTop: 4 }}>
                {folderStatus.error}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
