"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useApi } from "@/lib/hooks";

type Deployment = {
  id: string;
  name: string;
  template_id: string;
  status: string;
  provider: string;
  host?: string;
  port?: number;
  access_url?: string;
  created_at: string;
  started_at?: string;
  stopped_at?: string;
};

export default function DeploymentsPage() {
  const { get } = useApi();
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await get<Deployment[]>("/api/templates/deployments");
        setDeployments(data);
      } catch {
        // API may not be connected
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [get]);

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-semibold text-forest-dark">
            Deployments
          </h1>
          <p className="mt-1 text-sm text-forest-dark/60">
            Manage your running and stopped deployments.
          </p>
        </div>
        <Link
          href="/dashboard/templates"
          className="rounded-lg bg-forest px-4 py-2 text-sm font-medium text-white hover:bg-forest-hover transition-colors"
        >
          New deployment
        </Link>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-16 animate-pulse rounded-xl bg-white border border-mist"
            />
          ))}
        </div>
      ) : deployments.length === 0 ? (
        <div className="rounded-xl border border-mist bg-white p-12 text-center">
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
          {deployments.map((d) => (
            <Link
              key={d.id}
              href={`/dashboard/deployments/${d.id}`}
              className="flex items-center justify-between px-5 py-4 hover:bg-sage/50 transition-colors"
            >
              <div className="flex-1">
                <p className="text-sm font-medium text-forest-dark">
                  {d.name}
                </p>
                <p className="text-xs text-forest-dark/50 mt-0.5">
                  {d.template_id} &middot; {d.provider}
                  {d.access_url && (
                    <>
                      {" "}
                      &middot;{" "}
                      <span className="text-forest">{d.access_url}</span>
                    </>
                  )}
                </p>
              </div>
              <StatusBadge status={d.status} />
            </Link>
          ))}
        </div>
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
