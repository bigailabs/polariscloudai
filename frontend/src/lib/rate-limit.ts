/**
 * Simple in-memory sliding window rate limiter.
 * Works on edge runtime — no external dependencies.
 *
 * Note: In a multi-instance deployment (e.g. Cloudflare edge),
 * each isolate has its own counter. This is approximate but
 * sufficient to prevent abuse. For precise limits, use KV or Redis.
 */

type WindowEntry = {
  timestamps: number[];
};

const windows = new Map<string, WindowEntry>();

// Clean up stale entries every 5 minutes
const CLEANUP_INTERVAL = 5 * 60 * 1000;
let lastCleanup = Date.now();

function cleanup(now: number) {
  if (now - lastCleanup < CLEANUP_INTERVAL) return;
  lastCleanup = now;
  const cutoff = now - 60_000; // keep last minute
  for (const [key, entry] of windows) {
    entry.timestamps = entry.timestamps.filter((t) => t > cutoff);
    if (entry.timestamps.length === 0) windows.delete(key);
  }
}

export type RateLimitResult = {
  allowed: boolean;
  limit: number;
  remaining: number;
  resetAt: number; // epoch seconds
};

/**
 * Check if a request is allowed under the rate limit.
 * @param key - unique identifier (e.g. API key ID)
 * @param maxRequests - max requests per window
 * @param windowMs - window size in milliseconds (default 60s)
 */
export function checkRateLimit(
  key: string,
  maxRequests: number = 60,
  windowMs: number = 60_000
): RateLimitResult {
  const now = Date.now();
  cleanup(now);

  const cutoff = now - windowMs;
  let entry = windows.get(key);

  if (!entry) {
    entry = { timestamps: [] };
    windows.set(key, entry);
  }

  // Remove expired timestamps
  entry.timestamps = entry.timestamps.filter((t) => t > cutoff);

  const remaining = Math.max(0, maxRequests - entry.timestamps.length);
  const resetAt = Math.ceil((now + windowMs) / 1000);

  if (entry.timestamps.length >= maxRequests) {
    return { allowed: false, limit: maxRequests, remaining: 0, resetAt };
  }

  entry.timestamps.push(now);
  return { allowed: true, limit: maxRequests, remaining: remaining - 1, resetAt };
}
