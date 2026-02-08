import { createClient, SupabaseClient } from "@supabase/supabase-js";

let _client: SupabaseClient | null = null;

/** Server-side Supabase client using service role key (bypasses RLS). */
export const supabaseServer: SupabaseClient = new Proxy({} as SupabaseClient, {
  get(_target, prop) {
    if (!_client) {
      const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
      const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
      if (!url || !key) {
        throw new Error("SUPABASE_SERVICE_ROLE_KEY is not configured");
      }
      _client = createClient(url, key);
    }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return (_client as any)[prop as string];
  },
});
