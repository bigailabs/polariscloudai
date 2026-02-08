import posthog from "posthog-js";

/** Track a custom event. No-ops if PostHog isn't initialized. */
export function track(event: string, properties?: Record<string, unknown>) {
  if (typeof window !== "undefined" && posthog.__loaded) {
    posthog.capture(event, properties);
  }
}
