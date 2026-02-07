"use client";

import Link from "next/link";
import { useEffect, useState, useCallback } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type ServiceStatus = {
  name: string;
  status: "operational" | "degraded" | "outage";
  response_time_ms?: number;
  description: string;
};

type PlatformStatus = {
  overall_status: "operational" | "degraded" | "outage";
  services: ServiceStatus[];
  last_checked: string;
};

const STATUS_CONFIG = {
  operational: {
    label: "Operational",
    dot: "bg-fern",
    badge: "bg-fern/10 text-fern",
    bar: "bg-fern",
  },
  degraded: {
    label: "Degraded",
    dot: "bg-copper",
    badge: "bg-copper/10 text-copper",
    bar: "bg-copper",
  },
  outage: {
    label: "Outage",
    dot: "bg-red-500",
    badge: "bg-red-500/10 text-red-600",
    bar: "bg-red-500",
  },
} as const;

const OVERALL_CONFIG = {
  operational: {
    label: "All Systems Operational",
    bg: "bg-fern/5 border-fern/20",
    dot: "bg-fern",
    text: "text-fern",
  },
  degraded: {
    label: "Partial Service Disruption",
    bg: "bg-copper/5 border-copper/20",
    dot: "bg-copper",
    text: "text-copper",
  },
  outage: {
    label: "Major Outage",
    bg: "bg-red-500/5 border-red-500/20",
    dot: "bg-red-500",
    text: "text-red-600",
  },
} as const;

function UptimeBar() {
  const days = 90;
  return (
    <div className="flex gap-[2px]">
      {Array.from({ length: days }, (_, i) => (
        <div
          key={i}
          className="h-8 flex-1 rounded-[2px] bg-fern/80 hover:bg-fern transition-colors"
          title={`${days - i} days ago - Operational`}
        />
      ))}
    </div>
  );
}

function StatusBadge({ status }: { status: keyof typeof STATUS_CONFIG }) {
  const config = STATUS_CONFIG[status];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${config.badge}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${config.dot}`} />
      {config.label}
    </span>
  );
}

function ServiceRow({ service }: { service: ServiceStatus }) {
  return (
    <div className="flex items-center justify-between py-4 border-b border-mist last:border-b-0">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-3">
          <span
            className={`h-2.5 w-2.5 rounded-full shrink-0 ${STATUS_CONFIG[service.status].dot}`}
          />
          <div>
            <p className="text-sm font-medium text-forest-dark">
              {service.name}
            </p>
            <p className="text-xs text-forest-dark/50 mt-0.5">
              {service.description}
            </p>
          </div>
        </div>
      </div>
      <div className="flex items-center gap-3 shrink-0 ml-4">
        {service.response_time_ms !== undefined && (
          <span className="text-xs text-forest-dark/40 font-mono">
            {service.response_time_ms}ms
          </span>
        )}
        <StatusBadge status={service.status} />
      </div>
    </div>
  );
}

export default function StatusPage() {
  const [data, setData] = useState<PlatformStatus | null>(null);
  const [error, setError] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/status`, { cache: "no-store" });
      if (!res.ok) throw new Error("Failed to fetch status");
      const json: PlatformStatus = await res.json();
      setData(json);
      setError(false);
      setLastUpdated(new Date());
    } catch {
      setError(true);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30_000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const overall = data?.overall_status ?? "operational";
  const overallConfig = OVERALL_CONFIG[overall];

  return (
    <div className="flex min-h-screen flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-8 py-4 border-b border-mist">
        <Link href="/" className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-forest flex items-center justify-center">
            <span className="text-white font-bold text-sm">P</span>
          </div>
          <span className="text-lg font-semibold text-forest-dark">
            Polaris Computer
          </span>
        </Link>
        <nav className="flex items-center gap-4">
          <Link
            href="/"
            className="text-sm font-medium text-forest-dark/60 hover:text-forest transition-colors"
          >
            Home
          </Link>
          <span className="text-sm font-medium text-forest-dark">Status</span>
        </nav>
      </header>

      <main className="flex-1 w-full max-w-3xl mx-auto px-8 py-12">
        {/* Overall Status Banner */}
        <div
          className={`rounded-xl border p-6 ${overallConfig.bg} transition-colors duration-300`}
        >
          <div className="flex items-center gap-3">
            <span
              className={`h-4 w-4 rounded-full ${overallConfig.dot} animate-pulse`}
            />
            <h1 className={`text-xl font-semibold ${overallConfig.text}`}>
              {error ? "Unable to Reach API" : overallConfig.label}
            </h1>
          </div>
          {error && (
            <p className="mt-2 text-sm text-red-500/80 ml-7">
              Could not connect to the Polaris API. The service may be
              experiencing issues.
            </p>
          )}
        </div>

        {/* Last checked */}
        <div className="mt-4 flex items-center justify-between text-xs text-forest-dark/40">
          <span>
            {lastUpdated
              ? `Last checked: ${lastUpdated.toLocaleTimeString()}`
              : "Checking..."}
          </span>
          <span>Refreshes every 30 seconds</span>
        </div>

        {/* Services */}
        <section className="mt-10">
          <h2 className="text-sm font-semibold text-forest-dark/60 uppercase tracking-wide mb-4">
            Current Status
          </h2>
          <div className="rounded-xl border border-mist bg-white p-6">
            {data ? (
              data.services.map((service) => (
                <ServiceRow key={service.name} service={service} />
              ))
            ) : error ? (
              <div className="py-8 text-center">
                <p className="text-sm text-forest-dark/50">
                  Unable to load service status. Please try again later.
                </p>
              </div>
            ) : (
              <div className="py-8 text-center">
                <div className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-forest border-t-transparent" />
                <p className="mt-2 text-sm text-forest-dark/50">
                  Loading status...
                </p>
              </div>
            )}
          </div>
        </section>

        {/* Uptime */}
        <section className="mt-10">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-forest-dark/60 uppercase tracking-wide">
              Uptime — Last 90 Days
            </h2>
            <span className="text-sm font-medium text-fern">99.9% uptime</span>
          </div>
          <div className="rounded-xl border border-mist bg-white p-6">
            <UptimeBar />
            <div className="flex justify-between mt-2 text-xs text-forest-dark/30">
              <span>90 days ago</span>
              <span>Today</span>
            </div>
          </div>
        </section>

        {/* Incidents */}
        <section className="mt-10">
          <h2 className="text-sm font-semibold text-forest-dark/60 uppercase tracking-wide mb-4">
            Recent Incidents
          </h2>
          <div className="rounded-xl border border-mist bg-white p-8 text-center">
            <div className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-fern/10 mb-3">
              <svg
                className="h-5 w-5 text-fern"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={2}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <p className="text-sm font-medium text-forest-dark/70">
              No incidents in the last 30 days
            </p>
            <p className="mt-1 text-xs text-forest-dark/40">
              All systems have been operating normally.
            </p>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-mist px-8 py-6">
        <div className="max-w-3xl mx-auto flex items-center justify-between text-sm text-forest-dark/50">
          <span>Polaris Computer</span>
          <div className="flex items-center gap-4">
            <Link href="/" className="hover:text-forest transition-colors">
              Home
            </Link>
            <Link
              href="/pricing"
              className="hover:text-forest transition-colors"
            >
              Pricing
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
