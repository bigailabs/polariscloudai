"use client";

import { useEffect, useState } from "react";
import { useApi } from "@/lib/hooks";

type UsageData = {
  billing_month: string;
  total_minutes: number;
  total_cost_usd: number;
  records: {
    deployment_name: string;
    minutes: number;
    cost_usd: number;
    provider: string;
    machine_type: string;
  }[];
};

type CostSummary = {
  current_month_cost: number;
  current_month_minutes: number;
  compute_minutes_used: number;
  compute_minutes_limit: number;
};

type Limits = {
  tier: string;
  compute_minutes_limit: number;
  compute_minutes_used: number;
  storage_bytes_limit: number;
  storage_bytes_used: number;
};

export default function UsagePage() {
  const { get } = useApi();
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [costs, setCosts] = useState<CostSummary | null>(null);
  const [limits, setLimits] = useState<Limits | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [u, c, l] = await Promise.all([
          get<UsageData>("/api/usage").catch(() => null),
          get<CostSummary>("/api/costs").catch(() => null),
          get<Limits>("/api/limits").catch(() => null),
        ]);
        setUsage(u);
        setCosts(c);
        setLimits(l);
      } catch {
        // API not connected
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [get]);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-48 animate-pulse rounded bg-mist" />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-28 animate-pulse rounded-xl bg-white border border-mist" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-forest-dark">Usage</h1>
        <p className="mt-1 text-sm text-forest-dark/60">
          Monitor your compute usage and costs.
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 mb-8">
        <div className="rounded-xl border border-mist bg-white p-5">
          <p className="text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
            Current tier
          </p>
          <p className="mt-2 text-2xl font-semibold text-forest-dark capitalize">
            {limits?.tier || "free"}
          </p>
        </div>
        <div className="rounded-xl border border-mist bg-white p-5">
          <p className="text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
            Compute this month
          </p>
          <p className="mt-2 text-2xl font-semibold text-forest-dark">
            {costs?.current_month_minutes ?? limits?.compute_minutes_used ?? 0} min
          </p>
          {limits && (
            <div className="mt-2">
              <div className="h-1.5 rounded-full bg-mist">
                <div
                  className="h-1.5 rounded-full bg-forest transition-all"
                  style={{
                    width: `${Math.min(
                      ((limits.compute_minutes_used / limits.compute_minutes_limit) * 100) || 0,
                      100
                    )}%`,
                  }}
                />
              </div>
              <p className="mt-1 text-xs text-forest-dark/40">
                of {limits.compute_minutes_limit} min
              </p>
            </div>
          )}
        </div>
        <div className="rounded-xl border border-mist bg-white p-5">
          <p className="text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
            Cost this month
          </p>
          <p className="mt-2 text-2xl font-semibold text-forest-dark">
            ${costs?.current_month_cost?.toFixed(2) ?? "0.00"}
          </p>
        </div>
      </div>

      {/* Usage breakdown */}
      {usage && usage.records.length > 0 && (
        <div className="rounded-xl border border-mist bg-white p-5">
          <h2 className="text-sm font-semibold text-forest-dark mb-4">
            Breakdown — {usage.billing_month}
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-mist">
                  <th className="pb-3 text-left font-medium text-forest-dark/50">
                    Deployment
                  </th>
                  <th className="pb-3 text-left font-medium text-forest-dark/50">
                    Provider
                  </th>
                  <th className="pb-3 text-left font-medium text-forest-dark/50">
                    GPU
                  </th>
                  <th className="pb-3 text-right font-medium text-forest-dark/50">
                    Minutes
                  </th>
                  <th className="pb-3 text-right font-medium text-forest-dark/50">
                    Cost
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-mist">
                {usage.records.map((r, i) => (
                  <tr key={i}>
                    <td className="py-3 text-forest-dark">{r.deployment_name}</td>
                    <td className="py-3 text-forest-dark/60">{r.provider}</td>
                    <td className="py-3 text-forest-dark/60 font-mono text-xs">
                      {r.machine_type}
                    </td>
                    <td className="py-3 text-right text-forest-dark font-mono">
                      {r.minutes}
                    </td>
                    <td className="py-3 text-right text-forest-dark font-mono">
                      ${r.cost_usd.toFixed(4)}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t border-forest-dark/10">
                  <td colSpan={3} className="pt-3 font-medium text-forest-dark">
                    Total
                  </td>
                  <td className="pt-3 text-right font-medium text-forest-dark font-mono">
                    {usage.total_minutes}
                  </td>
                  <td className="pt-3 text-right font-medium text-forest-dark font-mono">
                    ${usage.total_cost_usd.toFixed(4)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
