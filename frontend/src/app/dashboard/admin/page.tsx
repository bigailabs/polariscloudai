"use client";

import { useEffect, useState } from "react";
import { useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useApi } from "@/lib/hooks";
import { ADMIN_EMAILS } from "@/lib/config";

type PlatformStats = {
  total_users: number;
  active_deployments: number;
  gpu_hours_today: number;
  revenue_this_month: number;
  users_by_tier: { free: number; basic: number; premium: number };
  deployments_by_status: Record<string, number>;
};

type ActivityItem = {
  id: string;
  type: "signup" | "deployment" | "error";
  message: string;
  timestamp: string;
  user_email?: string;
};

type SystemHealth = {
  api: "healthy" | "degraded" | "down";
  database: "healthy" | "degraded" | "down";
  gpu_providers: {
    verda: "healthy" | "degraded" | "down";
    targon: "healthy" | "degraded" | "down";
    local: "healthy" | "degraded" | "down";
  };
};

export default function AdminOverviewPage() {
  const { user } = useUser();
  const router = useRouter();
  const { get } = useApi();
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [health, setHealth] = useState<SystemHealth | null>(null);
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
        const data = await get<{
          stats: PlatformStats;
          activity: ActivityItem[];
          health: SystemHealth;
        }>("/api/admin/stats");
        setStats(data.stats);
        setActivity(data.activity);
        setHealth(data.health);
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
          Admin Overview
        </h1>
        <p className="mt-1 text-sm text-forest-dark/60">
          Platform-wide metrics and system health.
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
      ) : (
        <>
          {/* Stats cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
            <StatCard
              label="Total Users"
              value={stats?.total_users ?? 0}
              detail={
                stats
                  ? `${stats.users_by_tier.free} free / ${stats.users_by_tier.basic} basic / ${stats.users_by_tier.premium} premium`
                  : undefined
              }
            />
            <StatCard
              label="Active Deployments"
              value={stats?.active_deployments ?? 0}
            />
            <StatCard
              label="GPU Hours (today)"
              value={`${(stats?.gpu_hours_today ?? 0).toFixed(1)}h`}
            />
            <StatCard
              label="Revenue (this month)"
              value={`$${(stats?.revenue_this_month ?? 0).toFixed(2)}`}
            />
          </div>

          {/* System Health */}
          <div className="mt-8">
            <h2 className="text-lg font-semibold text-forest-dark mb-4">
              System Health
            </h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-5">
              <HealthCard label="API" status={health?.api ?? "down"} />
              <HealthCard label="Database" status={health?.database ?? "down"} />
              <HealthCard
                label="Verda"
                status={health?.gpu_providers.verda ?? "down"}
              />
              <HealthCard
                label="Targon"
                status={health?.gpu_providers.targon ?? "down"}
              />
              <HealthCard
                label="Local"
                status={health?.gpu_providers.local ?? "down"}
              />
            </div>
          </div>

          {/* Deployments by status */}
          {stats?.deployments_by_status && (
            <div className="mt-8">
              <h2 className="text-lg font-semibold text-forest-dark mb-4">
                Deployments by Status
              </h2>
              <div className="rounded-xl border border-mist bg-white p-5">
                <div className="flex flex-wrap gap-6">
                  {Object.entries(stats.deployments_by_status).map(
                    ([status, count]) => (
                      <div key={status} className="text-center">
                        <p className="text-2xl font-semibold text-forest-dark">
                          {count}
                        </p>
                        <p className="text-xs text-forest-dark/50 mt-1">
                          <StatusBadge status={status} />
                        </p>
                      </div>
                    )
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Activity Feed */}
          <div className="mt-8">
            <h2 className="text-lg font-semibold text-forest-dark mb-4">
              Live Activity
            </h2>
            {activity.length === 0 ? (
              <div className="rounded-xl border border-mist bg-white p-8 text-center">
                <p className="text-sm text-forest-dark/60">
                  No recent activity.
                </p>
              </div>
            ) : (
              <div className="rounded-xl border border-mist bg-white divide-y divide-mist">
                {activity.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center justify-between px-5 py-4"
                  >
                    <div className="flex items-center gap-3">
                      <ActivityIcon type={item.type} />
                      <div>
                        <p className="text-sm font-medium text-forest-dark">
                          {item.message}
                        </p>
                        {item.user_email && (
                          <p className="text-xs text-forest-dark/50 mt-0.5">
                            {item.user_email}
                          </p>
                        )}
                      </div>
                    </div>
                    <span className="text-xs text-forest-dark/40 whitespace-nowrap">
                      {formatRelativeTime(item.timestamp)}
                    </span>
                  </div>
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
  detail,
}: {
  label: string;
  value: string | number;
  detail?: string;
}) {
  return (
    <div className="rounded-xl border border-mist bg-white p-5">
      <p className="text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
        {label}
      </p>
      <p className="mt-2 text-2xl font-semibold text-forest-dark">{value}</p>
      {detail && (
        <p className="mt-1 text-xs text-forest-dark/40">{detail}</p>
      )}
    </div>
  );
}

function HealthCard({
  label,
  status,
}: {
  label: string;
  status: "healthy" | "degraded" | "down";
}) {
  const colors = {
    healthy: "bg-fern/10 text-fern border-fern/20",
    degraded: "bg-copper/10 text-copper border-copper/20",
    down: "bg-red-50 text-red-600 border-red-200",
  };

  const dots = {
    healthy: "bg-fern",
    degraded: "bg-copper",
    down: "bg-red-500",
  };

  return (
    <div
      className={`rounded-xl border p-4 ${colors[status]}`}
    >
      <div className="flex items-center gap-2">
        <span className={`h-2 w-2 rounded-full ${dots[status]}`} />
        <p className="text-sm font-medium">{label}</p>
      </div>
      <p className="mt-1 text-xs capitalize">{status}</p>
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

function ActivityIcon({ type }: { type: "signup" | "deployment" | "error" }) {
  const styles = {
    signup: "bg-fern/10 text-fern",
    deployment: "bg-forest/10 text-forest",
    error: "bg-red-50 text-red-600",
  };

  const icons = {
    signup: (
      <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M19 7.5v3m0 0v3m0-3h3m-3 0h-3m-2.25-4.125a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zM4 19.235v-.11a6.375 6.375 0 0112.75 0v.109A12.318 12.318 0 0110.374 21c-2.331 0-4.512-.645-6.374-1.766z" />
      </svg>
    ),
    deployment: (
      <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.631 8.41m5.96 5.96a14.926 14.926 0 01-5.841 2.58m-.119-8.54a6 6 0 00-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 00-2.58 5.84" />
      </svg>
    ),
    error: (
      <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
      </svg>
    ),
  };

  return (
    <div className={`flex items-center justify-center h-7 w-7 rounded-full ${styles[type]}`}>
      {icons[type]}
    </div>
  );
}

function formatRelativeTime(timestamp: string): string {
  const now = Date.now();
  const then = new Date(timestamp).getTime();
  const diff = Math.floor((now - then) / 1000);

  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}
