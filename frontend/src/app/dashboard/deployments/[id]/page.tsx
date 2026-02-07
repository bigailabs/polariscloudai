"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useApi } from "@/lib/hooks";
import { connectDeploymentWs, type DeploymentMessage } from "@/lib/websocket";

type DeploymentDetail = {
  id: string;
  name: string;
  template_id: string;
  status: string;
  provider: string;
  machine_type?: string;
  host?: string;
  port?: number;
  access_url?: string;
  error_message?: string;
  created_at: string;
  started_at?: string;
  stopped_at?: string;
};

type Metrics = {
  cpu_usage?: number;
  memory_usage?: number;
  gpu_usage?: number;
  uptime_seconds?: number;
};

export default function DeploymentDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const { get, post, getToken } = useApi();
  const [deployment, setDeployment] = useState<DeploymentDetail | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [logs, setLogs] = useState<DeploymentMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [d, m] = await Promise.all([
          get<DeploymentDetail>(`/api/templates/deployments/${id}`),
          get<Metrics>(`/api/deployments/${id}/metrics`).catch(() => null),
        ]);
        setDeployment(d);
        setMetrics(m);
      } catch {
        // deployment not found
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id, get]);

  // WebSocket for real-time progress
  useEffect(() => {
    if (!deployment || !["pending", "warming", "provisioning", "installing"].includes(deployment.status)) {
      return;
    }

    let ws: WebSocket | null = null;

    async function connect() {
      const token = await getToken();
      if (!token) return;

      ws = connectDeploymentWs(
        id,
        token,
        (msg) => {
          setLogs((prev) => [...prev, msg]);
          if (msg.status) {
            setDeployment((prev) =>
              prev ? { ...prev, status: msg.status! } : prev
            );
          }
        },
        () => {
          // reconnect on close if still in-progress
        }
      );
      wsRef.current = ws;
    }

    connect();

    return () => {
      ws?.close();
      wsRef.current = null;
    };
  }, [deployment?.status, id, getToken]);

  const handleStop = useCallback(async () => {
    try {
      await post(`/api/deployments/${id}/stop`);
      setDeployment((prev) =>
        prev ? { ...prev, status: "stopping" } : prev
      );
    } catch {
      // failed to stop
    }
  }, [id, post]);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-48 animate-pulse rounded bg-mist" />
        <div className="h-64 animate-pulse rounded-xl bg-white border border-mist" />
      </div>
    );
  }

  if (!deployment) {
    return (
      <div className="text-center py-16">
        <p className="text-sm text-forest-dark/60">Deployment not found.</p>
        <Link
          href="/dashboard/deployments"
          className="mt-4 inline-block text-sm font-medium text-forest hover:text-forest-hover"
        >
          Back to deployments
        </Link>
      </div>
    );
  }

  const isActive = ["running", "pending", "warming", "provisioning", "installing"].includes(
    deployment.status
  );

  return (
    <div>
      <div className="flex items-center gap-2 mb-1">
        <Link
          href="/dashboard/deployments"
          className="text-sm text-forest-dark/40 hover:text-forest-dark/60 transition-colors"
        >
          Deployments
        </Link>
        <span className="text-sm text-forest-dark/30">/</span>
      </div>

      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-semibold text-forest-dark">
            {deployment.name}
          </h1>
          <p className="mt-1 text-sm text-forest-dark/60">
            {deployment.template_id} &middot; {deployment.provider}
            {deployment.machine_type && ` &middot; ${deployment.machine_type}`}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={deployment.status} />
          {deployment.status === "running" && (
            <button
              onClick={handleStop}
              className="rounded-lg border border-red-200 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 transition-colors"
            >
              Stop
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Info card */}
        <div className="rounded-xl border border-mist bg-white p-5">
          <h2 className="text-sm font-semibold text-forest-dark mb-4">
            Details
          </h2>
          <dl className="space-y-3">
            <InfoRow label="ID" value={deployment.id} mono />
            <InfoRow label="Status" value={deployment.status} />
            {deployment.access_url && (
              <InfoRow label="URL">
                <a
                  href={deployment.access_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-forest hover:text-forest-hover font-mono"
                >
                  {deployment.access_url}
                </a>
              </InfoRow>
            )}
            {deployment.host && (
              <InfoRow
                label="Host"
                value={`${deployment.host}${deployment.port ? `:${deployment.port}` : ""}`}
                mono
              />
            )}
            <InfoRow label="Created" value={new Date(deployment.created_at).toLocaleString()} />
            {deployment.started_at && (
              <InfoRow label="Started" value={new Date(deployment.started_at).toLocaleString()} />
            )}
            {deployment.error_message && (
              <InfoRow label="Error">
                <span className="text-sm text-red-600">
                  {deployment.error_message}
                </span>
              </InfoRow>
            )}
          </dl>
        </div>

        {/* Metrics card */}
        {isActive && metrics && (
          <div className="rounded-xl border border-mist bg-white p-5">
            <h2 className="text-sm font-semibold text-forest-dark mb-4">
              Metrics
            </h2>
            <div className="space-y-4">
              {metrics.cpu_usage !== undefined && (
                <MetricBar label="CPU" value={metrics.cpu_usage} />
              )}
              {metrics.memory_usage !== undefined && (
                <MetricBar label="Memory" value={metrics.memory_usage} />
              )}
              {metrics.gpu_usage !== undefined && (
                <MetricBar label="GPU" value={metrics.gpu_usage} />
              )}
              {metrics.uptime_seconds !== undefined && (
                <div className="flex justify-between text-sm">
                  <span className="text-forest-dark/50">Uptime</span>
                  <span className="text-forest-dark font-mono">
                    {formatUptime(metrics.uptime_seconds)}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Logs */}
        {logs.length > 0 && (
          <div className="rounded-xl border border-mist bg-white p-5 lg:col-span-2">
            <h2 className="text-sm font-semibold text-forest-dark mb-4">
              Deployment logs
            </h2>
            <div className="max-h-64 overflow-y-auto rounded-lg bg-forest-dark p-4 font-mono text-xs text-lichen space-y-1">
              {logs.map((log, i) => (
                <div key={i}>
                  <span className="text-forest-dark/40 select-none">
                    {log.timestamp
                      ? new Date(log.timestamp).toLocaleTimeString()
                      : ""}
                    {" "}
                  </span>
                  {log.message || log.status || JSON.stringify(log)}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function InfoRow({
  label,
  value,
  mono,
  children,
}: {
  label: string;
  value?: string;
  mono?: boolean;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex justify-between">
      <dt className="text-sm text-forest-dark/50">{label}</dt>
      <dd className={`text-sm text-forest-dark ${mono ? "font-mono" : ""}`}>
        {children || value}
      </dd>
    </div>
  );
}

function MetricBar({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-forest-dark/50">{label}</span>
        <span className="text-forest-dark font-mono">{value.toFixed(1)}%</span>
      </div>
      <div className="h-2 rounded-full bg-mist">
        <div
          className="h-2 rounded-full bg-forest transition-all duration-500"
          style={{ width: `${Math.min(value, 100)}%` }}
        />
      </div>
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
    stopping: "bg-copper/10 text-copper",
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

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${h}h ${m}m ${s}s`;
}
