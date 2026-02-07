"use client";

import { useEffect, useState } from "react";
import { useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useApi } from "@/lib/hooks";
import { ADMIN_EMAILS } from "@/lib/config";

type ProviderStatus = {
  name: string;
  status: "healthy" | "degraded" | "down";
  total_gpus: number;
  in_use: number;
  available: number;
  gpu_types: { type: string; total: number; in_use: number }[];
};

type RegionMetrics = {
  region: string;
  total_capacity: number;
  in_use: number;
  available: number;
  providers: string[];
};

type ResourceData = {
  providers: ProviderStatus[];
  regions: RegionMetrics[];
  totals: {
    total_gpus: number;
    in_use: number;
    available: number;
    utilization_pct: number;
  };
};

export default function AdminResourcesPage() {
  const { user } = useUser();
  const router = useRouter();
  const { get } = useApi();
  const [data, setData] = useState<ResourceData | null>(null);
  const [loading, setLoading] = useState(true);

  const isAdmin =
    user?.primaryEmailAddress?.emailAddress &&
    ADMIN_EMAILS.includes(user.primaryEmailAddress.emailAddress);

  useEffect(() => {
    if (user && !isAdmin) {
      router.replace("/dashboard");
    }
  }, [user, isAdmin, router]);

  useEffect(() => {
    if (!isAdmin) return;
    async function load() {
      try {
        const result = await get<ResourceData>("/api/admin/resources");
        setData(result);
      } catch {
        // API may not be connected
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [get, isAdmin]);

  if (!isAdmin) return null;

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-forest-dark">
          Resource Monitoring
        </h1>
        <p className="mt-1 text-sm text-forest-dark/60">
          GPU utilization and provider health across the platform.
        </p>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="h-28 animate-pulse rounded-xl bg-white border border-mist"
            />
          ))}
        </div>
      ) : !data ? (
        <div className="rounded-xl border border-mist bg-white p-8 text-center">
          <p className="text-sm text-forest-dark/60">
            Unable to load resource data.
          </p>
        </div>
      ) : (
        <>
          {/* Overview cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
            <div className="rounded-xl border border-mist bg-white p-5">
              <p className="text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
                Total GPUs
              </p>
              <p className="mt-2 text-2xl font-semibold text-forest-dark">
                {data.totals.total_gpus}
              </p>
            </div>
            <div className="rounded-xl border border-mist bg-white p-5">
              <p className="text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
                In Use
              </p>
              <p className="mt-2 text-2xl font-semibold text-forest-dark">
                {data.totals.in_use}
              </p>
              <p className="mt-1 text-xs text-forest-dark/40">
                of {data.totals.total_gpus} total
              </p>
            </div>
            <div className="rounded-xl border border-mist bg-white p-5">
              <p className="text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
                Available
              </p>
              <p className="mt-2 text-2xl font-semibold text-fern">
                {data.totals.available}
              </p>
            </div>
            <div className="rounded-xl border border-mist bg-white p-5">
              <p className="text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
                Utilization
              </p>
              <p className="mt-2 text-2xl font-semibold text-forest-dark">
                {data.totals.utilization_pct.toFixed(1)}%
              </p>
              <div className="mt-2 h-2 rounded-full bg-mist overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    data.totals.utilization_pct > 90
                      ? "bg-red-500"
                      : data.totals.utilization_pct > 70
                        ? "bg-copper"
                        : "bg-fern"
                  }`}
                  style={{
                    width: `${Math.min(data.totals.utilization_pct, 100)}%`,
                  }}
                />
              </div>
            </div>
          </div>

          {/* Provider Status */}
          <div className="mt-8">
            <h2 className="text-lg font-semibold text-forest-dark mb-4">
              Provider Status
            </h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {data.providers.map((provider) => (
                <ProviderCard key={provider.name} provider={provider} />
              ))}
            </div>
          </div>

          {/* Regional Breakdown */}
          <div className="mt-8">
            <h2 className="text-lg font-semibold text-forest-dark mb-4">
              Regional Breakdown
            </h2>
            <div className="rounded-xl border border-mist bg-white overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-mist">
                      <th className="px-5 py-3 text-left text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
                        Region
                      </th>
                      <th className="px-5 py-3 text-left text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
                        Providers
                      </th>
                      <th className="px-5 py-3 text-left text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
                        Total Capacity
                      </th>
                      <th className="px-5 py-3 text-left text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
                        In Use
                      </th>
                      <th className="px-5 py-3 text-left text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
                        Available
                      </th>
                      <th className="px-5 py-3 text-left text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
                        Utilization
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-mist">
                    {data.regions.map((region) => {
                      const pct =
                        region.total_capacity > 0
                          ? (region.in_use / region.total_capacity) * 100
                          : 0;
                      return (
                        <tr
                          key={region.region}
                          className="hover:bg-sage/50 transition-colors"
                        >
                          <td className="px-5 py-4 text-sm font-medium text-forest-dark">
                            {region.region}
                          </td>
                          <td className="px-5 py-4">
                            <div className="flex gap-1.5">
                              {region.providers.map((p) => (
                                <span
                                  key={p}
                                  className="inline-flex items-center rounded-full bg-mist px-2 py-0.5 text-xs text-forest-dark/60 capitalize"
                                >
                                  {p}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td className="px-5 py-4 text-sm text-forest-dark/60">
                            {region.total_capacity} GPUs
                          </td>
                          <td className="px-5 py-4 text-sm text-forest-dark/60">
                            {region.in_use}
                          </td>
                          <td className="px-5 py-4 text-sm text-fern">
                            {region.available}
                          </td>
                          <td className="px-5 py-4">
                            <div className="flex items-center gap-2">
                              <div className="flex-1 h-2 rounded-full bg-mist overflow-hidden max-w-[80px]">
                                <div
                                  className={`h-full rounded-full ${
                                    pct > 90
                                      ? "bg-red-500"
                                      : pct > 70
                                        ? "bg-copper"
                                        : "bg-fern"
                                  }`}
                                  style={{
                                    width: `${Math.min(pct, 100)}%`,
                                  }}
                                />
                              </div>
                              <span className="text-xs text-forest-dark/50">
                                {pct.toFixed(0)}%
                              </span>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function ProviderCard({ provider }: { provider: ProviderStatus }) {
  const statusColors = {
    healthy: "bg-fern/10 text-fern border-fern/20",
    degraded: "bg-copper/10 text-copper border-copper/20",
    down: "bg-red-50 text-red-600 border-red-200",
  };

  const dotColors = {
    healthy: "bg-fern",
    degraded: "bg-copper",
    down: "bg-red-500",
  };

  const pct =
    provider.total_gpus > 0
      ? (provider.in_use / provider.total_gpus) * 100
      : 0;

  return (
    <div className="rounded-xl border border-mist bg-white p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-forest-dark capitalize">
          {provider.name}
        </h3>
        <span
          className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${statusColors[provider.status]}`}
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${dotColors[provider.status]}`}
          />
          {provider.status}
        </span>
      </div>

      <div className="flex items-end gap-4 mb-3">
        <div>
          <p className="text-2xl font-semibold text-forest-dark">
            {provider.in_use}
          </p>
          <p className="text-xs text-forest-dark/40">
            of {provider.total_gpus} GPUs in use
          </p>
        </div>
        <div className="flex-1">
          <div className="h-2 rounded-full bg-mist overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                pct > 90
                  ? "bg-red-500"
                  : pct > 70
                    ? "bg-copper"
                    : "bg-fern"
              }`}
              style={{ width: `${Math.min(pct, 100)}%` }}
            />
          </div>
        </div>
      </div>

      {provider.gpu_types.length > 0 && (
        <div className="border-t border-mist pt-3 mt-3 space-y-2">
          {provider.gpu_types.map((gpu) => (
            <div
              key={gpu.type}
              className="flex items-center justify-between text-xs"
            >
              <span className="text-forest-dark/60">{gpu.type}</span>
              <span className="text-forest-dark/40">
                {gpu.in_use}/{gpu.total}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
