"use client";

import { useEffect, useState } from "react";
import { useApi } from "@/lib/hooks";

type ApiKey = {
  id: string;
  name: string;
  key_prefix: string;
  request_count: number;
  is_active: boolean;
  created_at: string;
  last_used_at?: string;
  expires_at?: string;
};

export default function ApiKeysPage() {
  const { get, post, del } = useApi();
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [newKeyName, setNewKeyName] = useState("");
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  async function loadKeys() {
    try {
      const data = await get<ApiKey[]>("/api/keys");
      setKeys(data);
    } catch {
      // API not connected
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadKeys();
  }, [get]);

  async function createKey() {
    if (!newKeyName.trim()) return;
    setCreating(true);
    try {
      const result = await post<{ key: string; id: string }>(
        "/api/keys/generate",
        { name: newKeyName.trim() }
      );
      setCreatedKey(result.key);
      setNewKeyName("");
      loadKeys();
    } catch {
      // failed
    } finally {
      setCreating(false);
    }
  }

  async function deleteKey(id: string) {
    try {
      await del(`/api/keys/${id}`);
      setKeys((prev) => prev.filter((k) => k.id !== id));
    } catch {
      // failed
    }
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-forest-dark">API Keys</h1>
        <p className="mt-1 text-sm text-forest-dark/60">
          Manage API keys for programmatic access to your deployments.
        </p>
      </div>

      {/* Create new key */}
      <div className="rounded-xl border border-mist bg-white p-5 mb-6">
        <h2 className="text-sm font-semibold text-forest-dark mb-3">
          Create new key
        </h2>
        <div className="flex gap-3">
          <input
            type="text"
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && createKey()}
            placeholder="Key name (e.g., production-api)"
            className="flex-1 rounded-lg border border-mist px-3 py-2 text-sm text-forest-dark placeholder:text-forest-dark/30 focus:border-forest focus:outline-none"
          />
          <button
            onClick={createKey}
            disabled={creating || !newKeyName.trim()}
            className="rounded-lg bg-forest px-4 py-2 text-sm font-medium text-white hover:bg-forest-hover transition-colors disabled:opacity-50"
          >
            {creating ? "Creating..." : "Create"}
          </button>
        </div>

        {createdKey && (
          <div className="mt-4 rounded-lg bg-fern/5 border border-fern/20 p-4">
            <p className="text-xs text-fern font-medium mb-1">
              Key created! Copy it now — it won&apos;t be shown again.
            </p>
            <code className="block text-sm font-mono text-forest-dark bg-white rounded px-3 py-2 border border-mist select-all">
              {createdKey}
            </code>
          </div>
        )}
      </div>

      {/* Key list */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2].map((i) => (
            <div
              key={i}
              className="h-14 animate-pulse rounded-xl bg-white border border-mist"
            />
          ))}
        </div>
      ) : keys.length === 0 ? (
        <div className="rounded-xl border border-mist bg-white p-8 text-center">
          <p className="text-sm text-forest-dark/60">
            No API keys yet. Create one above.
          </p>
        </div>
      ) : (
        <div className="rounded-xl border border-mist bg-white divide-y divide-mist">
          {keys.map((key) => (
            <div
              key={key.id}
              className="flex items-center justify-between px-5 py-4"
            >
              <div>
                <p className="text-sm font-medium text-forest-dark">
                  {key.name}
                </p>
                <p className="text-xs text-forest-dark/50 font-mono mt-0.5">
                  {key.key_prefix}... &middot; {key.request_count} requests
                  {key.last_used_at &&
                    ` &middot; last used ${new Date(key.last_used_at).toLocaleDateString()}`}
                </p>
              </div>
              <button
                onClick={() => deleteKey(key.id)}
                className="rounded-lg border border-red-200 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 transition-colors"
              >
                Delete
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
