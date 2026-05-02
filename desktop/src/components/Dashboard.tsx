import { useEffect, useState } from "react";
import {
  listFolders,
  triggerSync,
  getSyncStatus,
  logout,
  getConflicts,
} from "../lib/tauri";
import type { Conflict, FolderInfo, SyncStatusResult } from "../lib/types";
import FolderList from "./FolderList";
import AddFolder from "./AddFolder";
import ConflictDialog from "./ConflictDialog";

interface Props {
  onLogout: () => void;
}

export default function Dashboard({ onLogout }: Props) {
  const [folders, setFolders] = useState<FolderInfo[]>([]);
  const [status, setStatus] = useState<SyncStatusResult | null>(null);
  const [conflicts, setConflicts] = useState<Conflict[]>([]);
  const [showAddFolder, setShowAddFolder] = useState(false);

  const refresh = async () => {
    const [f, s, c] = await Promise.all([
      listFolders(),
      getSyncStatus(),
      getConflicts(),
    ]);
    setFolders(f);
    setStatus(s);
    setConflicts(c);
  };

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleSync = async () => {
    await triggerSync();
    setTimeout(refresh, 500);
  };

  const handleLogout = async () => {
    await logout();
    onLogout();
  };

  const overall = status?.overall ?? "Idle";

  return (
    <div className="container">
      <div className="header">
        <h1>
          <span className={`status-dot ${overall.toLowerCase()}`} />
          Agent Dropbox
        </h1>
        <button className="secondary" onClick={handleLogout}>
          Disconnect
        </button>
      </div>

      {conflicts.length > 0 && (
        <ConflictDialog conflicts={conflicts} onResolved={refresh} />
      )}

      <FolderList folders={folders} status={status} onRefresh={refresh} />

      {showAddFolder ? (
        <AddFolder
          onAdded={() => {
            setShowAddFolder(false);
            refresh();
          }}
          onCancel={() => setShowAddFolder(false)}
        />
      ) : null}

      <div className="actions">
        <button className="primary" onClick={handleSync}>
          Sync Now
        </button>
        <button className="secondary" onClick={() => setShowAddFolder(true)}>
          Add Folder
        </button>
      </div>
    </div>
  );
}
