import { useEffect, useState } from "react";
import { getSettings, updateSettings } from "../lib/tauri";
import type { AppSettings } from "../lib/types";

interface Props {
  onClose: () => void;
}

export default function Settings({ onClose }: Props) {
  const [settings, setSettings] = useState<AppSettings | null>(null);

  useEffect(() => {
    getSettings().then(setSettings);
  }, []);

  const save = async () => {
    if (settings) {
      await updateSettings(settings);
      onClose();
    }
  };

  if (!settings) return null;

  return (
    <div className="container">
      <div className="header">
        <h1>Settings</h1>
        <button className="secondary" onClick={onClose}>
          Back
        </button>
      </div>

      <div style={{ flex: 1, overflowY: "auto" }}>
        <label style={{ display: "block", marginBottom: 12 }}>
          <span style={{ fontSize: 13 }}>Sync interval (seconds)</span>
          <input
            type="number"
            value={settings.sync_interval_secs}
            onChange={(e) =>
              setSettings({
                ...settings,
                sync_interval_secs: parseInt(e.target.value) || 30,
              })
            }
            style={{ marginTop: 4 }}
          />
        </label>

        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            marginBottom: 12,
            fontSize: 13,
          }}
        >
          <input
            type="checkbox"
            checked={settings.auto_sync}
            onChange={(e) =>
              setSettings({ ...settings, auto_sync: e.target.checked })
            }
            style={{ width: "auto" }}
          />
          Auto-sync on file changes
        </label>

        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            marginBottom: 12,
            fontSize: 13,
          }}
        >
          <input
            type="checkbox"
            checked={settings.launch_on_startup}
            onChange={(e) =>
              setSettings({
                ...settings,
                launch_on_startup: e.target.checked,
              })
            }
            style={{ width: "auto" }}
          />
          Launch on startup
        </label>

        <label style={{ display: "block", marginBottom: 12 }}>
          <span style={{ fontSize: 13 }}>Ignore patterns (one per line)</span>
          <textarea
            value={settings.ignore_patterns.join("\n")}
            onChange={(e) =>
              setSettings({
                ...settings,
                ignore_patterns: e.target.value
                  .split("\n")
                  .filter((p) => p.trim()),
              })
            }
            rows={5}
            style={{
              width: "100%",
              marginTop: 4,
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: 6,
              padding: "8px 12px",
              color: "var(--text)",
              fontSize: 13,
              resize: "vertical",
            }}
          />
        </label>
      </div>

      <div className="actions">
        <button className="primary" onClick={save}>
          Save
        </button>
        <button className="secondary" onClick={onClose}>
          Cancel
        </button>
      </div>
    </div>
  );
}
