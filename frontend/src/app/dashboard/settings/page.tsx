"use client";

import Link from "next/link";
import { useUser } from "@clerk/nextjs";

export default function SettingsPage() {
  const { user } = useUser();

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-forest-dark">Settings</h1>
        <p className="mt-1 text-sm text-forest-dark/60">
          Manage your account and preferences.
        </p>
      </div>

      <div className="space-y-6 max-w-2xl">
        {/* Profile */}
        <div className="rounded-xl border border-mist bg-white p-5">
          <h2 className="text-sm font-semibold text-forest-dark mb-4">
            Profile
          </h2>
          <dl className="space-y-3">
            <div className="flex justify-between">
              <dt className="text-sm text-forest-dark/50">Email</dt>
              <dd className="text-sm text-forest-dark">
                {user?.primaryEmailAddress?.emailAddress}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-sm text-forest-dark/50">Name</dt>
              <dd className="text-sm text-forest-dark">
                {user?.fullName || "—"}
              </dd>
            </div>
          </dl>
          <p className="mt-4 text-xs text-forest-dark/40">
            Profile is managed by Clerk. Click your avatar in the sidebar to update.
          </p>
        </div>

        {/* Billing link */}
        <div className="rounded-xl border border-mist bg-white p-5">
          <h2 className="text-sm font-semibold text-forest-dark mb-2">
            Billing
          </h2>
          <p className="text-sm text-forest-dark/60 mb-4">
            Manage your subscription and payment methods.
          </p>
          <Link
            href="/dashboard/settings/billing"
            className="rounded-lg bg-forest px-4 py-2 text-sm font-medium text-white hover:bg-forest-hover transition-colors"
          >
            Manage billing
          </Link>
        </div>

        {/* Webhooks placeholder */}
        <div className="rounded-xl border border-mist bg-white p-5">
          <h2 className="text-sm font-semibold text-forest-dark mb-2">
            Webhooks
          </h2>
          <p className="text-sm text-forest-dark/60">
            Configure webhook endpoints to receive deployment events. Coming soon.
          </p>
        </div>
      </div>
    </div>
  );
}
