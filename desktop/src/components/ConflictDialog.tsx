import { resolveConflict } from "../lib/tauri";
import type { Conflict } from "../lib/types";

interface Props {
  conflicts: Conflict[];
  onResolved: () => void;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function ConflictDialog({ conflicts, onResolved }: Props) {
  const handleResolve = async (
    id: string,
    resolution: "KeepLocal" | "KeepRemote" | "KeepBoth"
  ) => {
    await resolveConflict(id, resolution);
    onResolved();
  };

  return (
    <div style={{ marginBottom: 12 }}>
      <div
        style={{
          color: "var(--warning)",
          fontWeight: 500,
          fontSize: 13,
          marginBottom: 6,
        }}
      >
        {conflicts.length} conflict{conflicts.length > 1 ? "s" : ""} detected
      </div>
      {conflicts.map((c) => (
        <div key={c.id} className="conflict-item">
          <div style={{ fontWeight: 500, fontSize: 13 }}>
            {c.folder_name}/{c.path}
          </div>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              fontSize: 12,
              color: "var(--text-dim)",
              marginTop: 4,
            }}
          >
            <span>Local: {formatSize(c.local_size)}</span>
            <span>Remote: {formatSize(c.remote_size)}</span>
          </div>
          <div className="conflict-actions">
            <button
              className="primary"
              onClick={() => handleResolve(c.id, "KeepLocal")}
            >
              Keep Local
            </button>
            <button
              className="secondary"
              onClick={() => handleResolve(c.id, "KeepRemote")}
            >
              Keep Remote
            </button>
            <button
              className="secondary"
              onClick={() => handleResolve(c.id, "KeepBoth")}
            >
              Keep Both
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
