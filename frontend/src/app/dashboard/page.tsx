"use client";

import { useEffect, useState } from "react";
import { useUser } from "@clerk/nextjs";
import Link from "next/link";
import { useApi } from "@/lib/hooks";

type Stats = {
  compute_minutes_used: number;
  compute_minutes_limit: number;
  storage_bytes_used: number;
  storage_bytes_limit: number;
  active_deployments: number;
  total_deployments: number;
};

type DeploymentSummary = {
  id: string;
  name: string;
  template_id: string;
  status: string;
  created_at: string;
};

export default function DashboardPage() {
  const { user } = useUser();
  const { get } = useApi();
  const [stats, setStats] = useState<Stats | null>(null);
  const [deployments, setDeployments] = useState<DeploymentSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [s, d] = await Promise.all([
          get<Stats>("/api/stats"),
          get<DeploymentSummary[]>("/api/templates/deployments"),
        ]);
        setStats(s);
        setDeployments(d);
      } catch {
        // API may not be connected yet
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [get]);

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-forest-dark">
          Welcome back{user?.firstName ? `, ${user.firstName}` : ""}
        </h1>
        <p className="mt-1 text-sm text-forest-dark/60">
          Here&apos;s what&apos;s happening with your deployments.
        </p>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-28 animate-pulse rounded-xl bg-white border border-mist"
            />
          ))}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard
              label="Active deployments"
              value={stats?.active_deployments ?? 0}
              total={stats?.total_deployments}
            />
            <StatCard
              label="Compute used"
              value={`${stats?.compute_minutes_used ?? 0} min`}
              total={stats?.compute_minutes_limit ? `${stats.compute_minutes_limit} min` : undefined}
            />
            <StatCard
              label="Storage used"
              value={formatBytes(stats?.storage_bytes_used ?? 0)}
              total={stats?.storage_bytes_limit ? formatBytes(stats.storage_bytes_limit) : undefined}
            />
          </div>

          <div className="mt-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-forest-dark">
                Recent deployments
              </h2>
              <Link
                href="/dashboard/deployments"
                className="text-sm font-medium text-forest hover:text-forest-hover transition-colors"
              >
                View all
              </Link>
            </div>

            {deployments.length === 0 ? (
              <div className="rounded-xl border border-mist bg-white p-8 text-center">
                <p className="text-sm text-forest-dark/60">
                  No deployments yet.{" "}
                  <Link
                    href="/dashboard/templates"
                    className="font-medium text-forest hover:text-forest-hover"
                  >
                    Deploy a template
                  </Link>{" "}
                  to get started.
                </p>
              </div>
            ) : (
              <div className="rounded-xl border border-mist bg-white divide-y divide-mist">
                {deployments.slice(0, 5).map((d) => (
                  <Link
                    key={d.id}
                    href={`/dashboard/deployments/${d.id}`}
                    className="flex items-center justify-between px-5 py-4 hover:bg-sage/50 transition-colors"
                  >
                    <div>
                      <p className="text-sm font-medium text-forest-dark">
                        {d.name}
                      </p>
                      <p className="text-xs text-forest-dark/50 mt-0.5">
                        {d.template_id}
                      </p>
                    </div>
                    <StatusBadge status={d.status} />
                  </Link>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  total,
}: {
  label: string;
  value: string | number;
  total?: string | number;
}) {
  return (
    <div className="rounded-xl border border-mist bg-white p-5">
      <p className="text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
        {label}
      </p>
      <p className="mt-2 text-2xl font-semibold text-forest-dark">{value}</p>
      {total !== undefined && (
        <p className="mt-1 text-xs text-forest-dark/40">of {total}</p>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    running: "bg-fern/10 text-fern",
    stopped: "bg-stone text-forest-dark/50",
    failed: "bg-red-50 text-red-600",
    pending: "bg-copper/10 text-copper",
    provisioning: "bg-copper/10 text-copper",
    installing: "bg-copper/10 text-copper",
    warming: "bg-copper/10 text-copper",
  };

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
        colors[status] || "bg-mist text-forest-dark/60"
      }`}
    >
      {status}
    </span>
  );
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}
