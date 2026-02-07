"use client";

import { SignUp } from "@clerk/nextjs";
import { AT_CAPACITY } from "@/lib/config";
import { WaitlistForm } from "@/components/waitlist-form";
import Link from "next/link";

export default function SignUpPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-sage">
      {AT_CAPACITY ? (
        <div className="w-full max-w-md rounded-xl border border-mist bg-white p-8 shadow-lg">
          {/* Logo */}
          <div className="mb-6 flex justify-center">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-forest">
              <span className="text-lg font-bold text-white">P</span>
            </div>
          </div>

          {/* Headline */}
          <h1 className="mb-3 text-center text-2xl font-semibold tracking-tight text-forest-dark">
            We&apos;re at capacity
          </h1>

          {/* Body */}
          <p className="mb-6 text-center text-sm leading-relaxed text-forest-dark/70">
            To maintain reliable, low-latency inference for every user, we&apos;ve
            temporarily paused new signups. Leave your email and we&apos;ll notify
            you when a spot opens.
          </p>

          {/* Waitlist form */}
          <WaitlistForm variant="inline" />

          {/* Links */}
          <div className="mt-6 flex flex-col items-center gap-2 text-sm">
            <p className="text-forest-dark/70">
              Already have an account?{" "}
              <Link
                href="/sign-in"
                className="font-medium text-forest hover:text-fern transition-colors"
              >
                Sign in
              </Link>
            </p>
            <Link
              href="/pricing"
              className="font-medium text-forest hover:text-fern transition-colors"
            >
              View our pricing &rarr;
            </Link>
          </div>
        </div>
      ) : (
        <SignUp
          appearance={{
            elements: {
              rootBox: "mx-auto",
              card: "shadow-lg border border-mist",
            },
          }}
        />
      )}
    </div>
  );
}
