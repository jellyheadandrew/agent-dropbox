import { useState } from "react";
import { addFolder } from "../lib/tauri";

interface Props {
  onAdded: () => void;
  onCancel: () => void;
}

export default function AddFolder({ onAdded, onCancel }: Props) {
  const [name, setName] = useState("");
  const [path, setPath] = useState("");
  const [error, setError] = useState("");

  const handleAdd = async () => {
    if (!name.trim() || !path.trim()) {
      setError("Name and path are required");
      return;
    }

    try {
      await addFolder(name.trim(), path.trim());
      onAdded();
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: 12,
        marginBottom: 8,
      }}
    >
      <div style={{ marginBottom: 8, fontWeight: 500 }}>Add Sync Folder</div>
      <input
        placeholder="Folder name (e.g., Documents)"
        value={name}
        onChange={(e) => setName(e.target.value)}
        style={{ marginBottom: 8 }}
      />
      <input
        placeholder="Local path (e.g., C:\Users\me\Documents)"
        value={path}
        onChange={(e) => setPath(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleAdd()}
      />
      {error && (
        <p className="error-text" style={{ marginTop: 4 }}>
          {error}
        </p>
      )}
      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
        <button className="primary" onClick={handleAdd}>
          Add
        </button>
        <button className="secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}
