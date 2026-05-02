import { useState } from "react";
import { pair } from "../lib/tauri";

interface Props {
  onLogin: () => void;
}

export default function Login({ onLogin }: Props) {
  const [serverUrl, setServerUrl] = useState("");
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handlePair = async () => {
    if (!serverUrl.trim() || !token.trim()) {
      setError("Server URL and token are required");
      return;
    }

    setLoading(true);
    setError("");

    try {
      await pair(serverUrl.trim(), token.trim());
      onLogin();
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <h1>Agent Dropbox</h1>
      <p className="subtitle">Connect to your sync server</p>

      <input
        type="text"
        placeholder="Server URL (e.g., https://sync.example.com)"
        value={serverUrl}
        onChange={(e) => setServerUrl(e.target.value)}
      />

      <input
        type="text"
        placeholder="Pairing Token (ADBOX-XXXX-XXXX-XXXX-XXXX)"
        value={token}
        onChange={(e) => setToken(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handlePair()}
      />

      {error && <p className="error-text">{error}</p>}

      <button className="primary" onClick={handlePair} disabled={loading}>
        {loading ? "Connecting..." : "Connect"}
      </button>
    </div>
  );
}
