"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useApi } from "@/lib/hooks";

type BillingStatus = {
  tier: string;
  stripe_customer_id?: string;
  stripe_subscription_id?: string;
  current_period_end?: string;
};

export default function BillingPage() {
  const { get, post } = useApi();
  const [billing, setBilling] = useState<BillingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [upgrading, setUpgrading] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const data = await get<BillingStatus>("/api/billing/status");
        setBilling(data);
      } catch {
        // billing not enabled
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [get]);

  async function handleUpgrade(tier: string) {
    setUpgrading(true);
    try {
      const result = await post<{ checkout_url: string }>(
        "/api/billing/checkout",
        { tier }
      );
      window.location.href = result.checkout_url;
    } catch {
      setUpgrading(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-48 animate-pulse rounded bg-mist" />
        <div className="h-64 animate-pulse rounded-xl bg-white border border-mist" />
      </div>
    );
  }

  const plans = [
    {
      id: "free",
      name: "Free",
      price: "$0",
      features: ["30 compute minutes/mo", "No persistent storage", "Community support"],
    },
    {
      id: "basic",
      name: "Basic",
      price: "$10",
      features: ["300 compute minutes/mo", "10 GB storage", "Email support"],
    },
    {
      id: "premium",
      name: "Premium",
      price: "$20",
      features: ["1,000 compute minutes/mo", "100 GB storage", "Priority support"],
    },
  ];

  return (
    <div>
      <div className="flex items-center gap-2 mb-1">
        <Link
          href="/dashboard/settings"
          className="text-sm text-forest-dark/40 hover:text-forest-dark/60 transition-colors"
        >
          Settings
        </Link>
        <span className="text-sm text-forest-dark/30">/</span>
      </div>

      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-forest-dark">Billing</h1>
        <p className="mt-1 text-sm text-forest-dark/60">
          Current plan:{" "}
          <span className="font-medium text-forest-dark capitalize">
            {billing?.tier || "free"}
          </span>
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 max-w-3xl">
        {plans.map((plan) => {
          const isCurrent = billing?.tier === plan.id;
          return (
            <div
              key={plan.id}
              className={`rounded-xl border p-5 ${
                isCurrent
                  ? "border-forest bg-forest/5"
                  : "border-mist bg-white"
              }`}
            >
              <h3 className="text-sm font-semibold text-forest-dark">
                {plan.name}
              </h3>
              <p className="mt-1 text-2xl font-bold text-forest-dark">
                {plan.price}
                <span className="text-sm font-normal text-forest-dark/50">
                  /mo
                </span>
              </p>
              <ul className="mt-4 space-y-2">
                {plan.features.map((f) => (
                  <li
                    key={f}
                    className="flex items-center gap-2 text-xs text-forest-dark/60"
                  >
                    <span className="text-fern">&#10003;</span>
                    {f}
                  </li>
                ))}
              </ul>
              <div className="mt-5">
                {isCurrent ? (
                  <span className="text-xs font-medium text-forest">
                    Current plan
                  </span>
                ) : (
                  <button
                    onClick={() => handleUpgrade(plan.id)}
                    disabled={upgrading}
                    className="w-full rounded-lg border border-forest px-3 py-2 text-xs font-medium text-forest hover:bg-forest hover:text-white transition-colors disabled:opacity-50"
                  >
                    {upgrading ? "Redirecting..." : plan.id === "free" ? "Downgrade" : "Upgrade"}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
