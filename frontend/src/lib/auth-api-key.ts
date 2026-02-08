import { supabaseServer } from "./supabase-server";

export type ApiKeyRecord = {
  id: string;
  user_id: string;
  name: string;
  key_prefix: string;
  request_count: number;
  is_active: boolean;
};

/** Hash a raw API key using SHA-256 (edge-compatible). */
async function hashKey(rawKey: string): Promise<string> {
  const encoded = new TextEncoder().encode(rawKey);
  const digest = await crypto.subtle.digest("SHA-256", encoded);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

/**
 * Validate a Bearer token as a Polaris API key.
 * Returns the key record if valid, null otherwise.
 */
export async function validateApiKey(
  rawKey: string
): Promise<ApiKeyRecord | null> {
  if (!rawKey.startsWith("pi_sk_")) return null;

  const keyHash = await hashKey(rawKey);

  const { data, error } = await supabaseServer
    .from("api_keys")
    .select("id, user_id, name, key_prefix, request_count, is_active")
    .eq("key_hash", keyHash)
    .eq("is_active", true)
    .single();

  if (error || !data) return null;
  return data as ApiKeyRecord;
}

/** Increment request_count and update last_used_at for a key. */
export async function recordKeyUsage(keyId: string): Promise<void> {
  await supabaseServer.rpc("increment_request_count", { key_id: keyId });
}

/**
 * Fallback: increment via direct update if the RPC doesn't exist.
 * Call this instead of recordKeyUsage if you haven't created the RPC.
 */
export async function recordKeyUsageDirect(keyId: string): Promise<void> {
  const { data } = await supabaseServer
    .from("api_keys")
    .select("request_count")
    .eq("id", keyId)
    .single();

  await supabaseServer
    .from("api_keys")
    .update({
      request_count: (data?.request_count ?? 0) + 1,
      last_used_at: new Date().toISOString(),
    })
    .eq("id", keyId);
}
