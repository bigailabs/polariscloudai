"use client";

import { useEffect, useState, useCallback } from "react";
import { useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useApi } from "@/lib/hooks";
import { ADMIN_EMAILS } from "@/lib/config";

type AdminDeployment = {
  id: string;
  user_email: string;
  name: string;
  template_id: string;
  provider: string;
  status: string;
  created_at: string;
  cost_usd: number;
};

type DeploymentsResponse = {
  deployments: AdminDeployment[];
  total: number;
  page: number;
  per_page: number;
};

export default function AdminDeploymentsPage() {
  const { user } = useUser();
  const router = useRouter();
  const { get, put } = useApi();
  const [data, setData] = useState<DeploymentsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("all");
  const [providerFilter, setProviderFilter] = useState("all");
  const [templateFilter, setTemplateFilter] = useState("all");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [bulkLoading, setBulkLoading] = useState(false);

  const isAdmin =
    user?.primaryEmailAddress?.emailAddress &&
    ADMIN_EMAILS.includes(user.primaryEmailAddress.emailAddress);

  useEffect(() => {
    if (user && !isAdmin) {
      router.replace("/dashboard");
    }
  }, [user, isAdmin, router]);

  const loadDeployments = useCallback(async () => {
    if (!isAdmin) return;
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: String(page),
        per_page: "20",
      });
      if (statusFilter !== "all") params.set("status", statusFilter);
      if (providerFilter !== "all") params.set("provider", providerFilter);
      if (templateFilter !== "all") params.set("template_id", templateFilter);

      const result = await get<DeploymentsResponse>(
        `/api/admin/deployments?${params}`
      );
      setData(result);
    } catch {
      // API may not be connected
    } finally {
      setLoading(false);
    }
  }, [get, isAdmin, page, statusFilter, providerFilter, templateFilter]);

  useEffect(() => {
    loadDeployments();
  }, [loadDeployments]);

  function toggleSelect(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleSelectAll() {
    if (!data) return;
    if (selected.size === data.deployments.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(data.deployments.map((d) => d.id)));
    }
  }

  async function handleBulkTerminate() {
    if (selected.size === 0) return;
    const confirmed = window.confirm(
      `Terminate ${selected.size} deployment(s)? This cannot be undone.`
    );
    if (!confirmed) return;

    setBulkLoading(true);
    try {
      for (const id of selected) {
        await put(`/api/admin/deployments/${id}/terminate`);
      }
      setSelected(new Set());
      await loadDeployments();
    } catch {
      // Handle error
    } finally {
      setBulkLoading(false);
    }
  }

  if (!isAdmin) return null;

  const totalPages = data ? Math.ceil(data.total / data.per_page) : 0;

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-forest-dark">
          All Deployments
        </h1>
        <p className="mt-1 text-sm text-forest-dark/60">
          View and manage deployments across all users.
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-mist bg-white px-4 py-2.5 text-sm text-forest-dark focus:border-forest focus:outline-none focus:ring-1 focus:ring-forest"
        >
          <option value="all">All statuses</option>
          <option value="running">Running</option>
          <option value="pending">Pending</option>
          <option value="provisioning">Provisioning</option>
          <option value="installing">Installing</option>
          <option value="warming">Warming</option>
          <option value="stopped">Stopped</option>
          <option value="failed">Failed</option>
        </select>
        <select
          value={providerFilter}
          onChange={(e) => {
            setProviderFilter(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-mist bg-white px-4 py-2.5 text-sm text-forest-dark focus:border-forest focus:outline-none focus:ring-1 focus:ring-forest"
        >
          <option value="all">All providers</option>
          <option value="verda">Verda</option>
          <option value="targon">Targon</option>
          <option value="local">Local</option>
        </select>
        <select
          value={templateFilter}
          onChange={(e) => {
            setTemplateFilter(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-mist bg-white px-4 py-2.5 text-sm text-forest-dark focus:border-forest focus:outline-none focus:ring-1 focus:ring-forest"
        >
          <option value="all">All templates</option>
          <option value="jupyter">Jupyter</option>
          <option value="vscode">VS Code</option>
          <option value="comfyui">ComfyUI</option>
          <option value="llama">Llama</option>
        </select>

        {selected.size > 0 && (
          <button
            onClick={handleBulkTerminate}
            disabled={bulkLoading}
            className="ml-auto rounded-lg bg-red-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-red-700 transition-colors disabled:opacity-50"
          >
            {bulkLoading
              ? "Terminating..."
              : `Terminate ${selected.size} selected`}
          </button>
        )}
      </div>

      {/* Table */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="h-16 animate-pulse rounded-xl bg-white border border-mist"
            />
          ))}
        </div>
      ) : !data || data.deployments.length === 0 ? (
        <div className="rounded-xl border border-mist bg-white p-8 text-center">
          <p className="text-sm text-forest-dark/60">No deployments found.</p>
        </div>
      ) : (
        <>
          <div className="rounded-xl border border-mist bg-white overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-mist">
                    <th className="px-5 py-3 text-left">
                      <input
                        type="checkbox"
                        checked={selected.size === data.deployments.length}
                        onChange={toggleSelectAll}
                        className="h-4 w-4 rounded border-mist text-forest focus:ring-forest"
                      />
                    </th>
                    <th className="px-5 py-3 text-left text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
                      User
                    </th>
                    <th className="px-5 py-3 text-left text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
                      Name
                    </th>
                    <th className="px-5 py-3 text-left text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
                      Template
                    </th>
                    <th className="px-5 py-3 text-left text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
                      Provider
                    </th>
                    <th className="px-5 py-3 text-left text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
                      Status
                    </th>
                    <th className="px-5 py-3 text-left text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
                      Created
                    </th>
                    <th className="px-5 py-3 text-right text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
                      Cost
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-mist">
                  {data.deployments.map((d) => (
                    <tr
                      key={d.id}
                      className={`transition-colors ${
                        selected.has(d.id)
                          ? "bg-forest/5"
                          : "hover:bg-sage/50"
                      }`}
                    >
                      <td className="px-5 py-4">
                        <input
                          type="checkbox"
                          checked={selected.has(d.id)}
                          onChange={() => toggleSelect(d.id)}
                          className="h-4 w-4 rounded border-mist text-forest focus:ring-forest"
                        />
                      </td>
                      <td className="px-5 py-4 text-sm text-forest-dark/60">
                        {d.user_email}
                      </td>
                      <td className="px-5 py-4 text-sm font-medium text-forest-dark">
                        {d.name}
                      </td>
                      <td className="px-5 py-4">
                        <span className="inline-flex items-center rounded-full bg-mist px-2.5 py-0.5 text-xs font-medium text-forest-dark/60">
                          {d.template_id}
                        </span>
                      </td>
                      <td className="px-5 py-4">
                        <ProviderBadge provider={d.provider} />
                      </td>
                      <td className="px-5 py-4">
                        <StatusBadge status={d.status} />
                      </td>
                      <td className="px-5 py-4 text-sm text-forest-dark/40">
                        {formatRelativeTime(d.created_at)}
                      </td>
                      <td className="px-5 py-4 text-sm text-forest-dark/60 text-right">
                        ${d.cost_usd.toFixed(4)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-4 flex items-center justify-between">
              <p className="text-sm text-forest-dark/50">
                Showing {(page - 1) * 20 + 1}--
                {Math.min(page * 20, data.total)} of {data.total} deployments
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page === 1}
                  className="rounded-lg border border-mist bg-white px-3 py-1.5 text-sm font-medium text-forest-dark hover:bg-mist transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage(Math.min(totalPages, page + 1))}
                  disabled={page === totalPages}
                  className="rounded-lg border border-mist bg-white px-3 py-1.5 text-sm font-medium text-forest-dark hover:bg-mist transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
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

function ProviderBadge({ provider }: { provider: string }) {
  const colors: Record<string, string> = {
    verda: "bg-forest/10 text-forest",
    targon: "bg-copper/10 text-copper",
    local: "bg-mist text-forest-dark/60",
  };

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${
        colors[provider] || "bg-mist text-forest-dark/60"
      }`}
    >
      {provider}
    </span>
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
