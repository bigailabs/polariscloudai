"use client";

import { useState } from "react";
import { joinWaitlist } from "@/lib/supabase";

type Variant = "hero" | "inline";
type Status = "idle" | "loading" | "joined" | "already_joined" | "error";

export function WaitlistForm({ variant = "hero" }: { variant?: Variant }) {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [errorMsg, setErrorMsg] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;

    setStatus("loading");
    const result = await joinWaitlist(email.trim());

    if (result.status === "joined") {
      setStatus("joined");
    } else if (result.status === "already_joined") {
      setStatus("already_joined");
    } else {
      setErrorMsg(result.message);
      setStatus("error");
    }
  }

  if (status === "joined") {
    return (
      <div className={variant === "hero" ? "text-center" : ""}>
        <div className={`inline-flex items-center gap-2 rounded-lg bg-fern/10 px-4 ${variant === "hero" ? "py-3" : "py-2"}`}>
          <span className="text-fern text-lg">&#10003;</span>
          <span className={`font-medium text-forest-dark ${variant === "hero" ? "text-base" : "text-sm"}`}>
            You&apos;re on the list. We&apos;ll email you when a spot opens up.
          </span>
        </div>
      </div>
    );
  }

  if (status === "already_joined") {
    return (
      <div className={variant === "hero" ? "text-center" : ""}>
        <div className={`inline-flex items-center gap-2 rounded-lg bg-forest/5 px-4 ${variant === "hero" ? "py-3" : "py-2"}`}>
          <span className="text-forest text-lg">&#10003;</span>
          <span className={`font-medium text-forest-dark ${variant === "hero" ? "text-base" : "text-sm"}`}>
            You&apos;re already on the waitlist. We&apos;ll be in touch soon.
          </span>
        </div>
      </div>
    );
  }

  const isHero = variant === "hero";

  return (
    <form onSubmit={handleSubmit} className={isHero ? "w-full max-w-md mx-auto" : "w-full max-w-sm"}>
      <div className={`flex ${isHero ? "gap-3" : "gap-2"}`}>
        <input
          type="email"
          required
          placeholder="you@company.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className={`flex-1 rounded-lg border border-mist bg-white text-forest-dark placeholder:text-lichen focus:outline-none focus:ring-2 focus:ring-forest/30 focus:border-forest transition-colors ${
            isHero ? "px-4 py-3 text-base" : "px-3 py-2 text-sm"
          }`}
        />
        <button
          type="submit"
          disabled={status === "loading"}
          className={`rounded-lg bg-forest font-medium text-white hover:bg-forest-hover transition-colors disabled:opacity-60 whitespace-nowrap ${
            isHero ? "px-6 py-3 text-base" : "px-4 py-2 text-sm"
          }`}
        >
          {status === "loading" ? "Joining..." : "Join Waitlist"}
        </button>
      </div>
      {status === "error" && (
        <p className="mt-2 text-sm text-red-600">{errorMsg || "Something went wrong. Please try again."}</p>
      )}
    </form>
  );
}
