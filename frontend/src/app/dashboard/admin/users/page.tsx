"use client";

import { useEffect, useState, useCallback } from "react";
import { useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useApi } from "@/lib/hooks";
import { ADMIN_EMAILS } from "@/lib/config";

type AdminUser = {
  id: string;
  email: string;
  name: string | null;
  tier: string;
  active_deployments: number;
  compute_minutes_used: number;
  last_active_at: string | null;
  created_at: string;
  is_suspended: boolean;
};

type UsersResponse = {
  users: AdminUser[];
  total: number;
  page: number;
  per_page: number;
};

export default function AdminUsersPage() {
  const { user } = useUser();
  const router = useRouter();
  const { get, put } = useApi();
  const [data, setData] = useState<UsersResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [tierFilter, setTierFilter] = useState("all");
  const [page, setPage] = useState(1);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const isAdmin =
    user?.primaryEmailAddress?.emailAddress &&
    ADMIN_EMAILS.includes(user.primaryEmailAddress.emailAddress);

  useEffect(() => {
    if (user && !isAdmin) {
      router.replace("/dashboard");
    }
  }, [user, isAdmin, router]);

  const loadUsers = useCallback(async () => {
    if (!isAdmin) return;
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: String(page),
        per_page: "20",
      });
      if (search) params.set("search", search);
      if (tierFilter !== "all") params.set("tier", tierFilter);

      const result = await get<UsersResponse>(`/api/admin/users?${params}`);
      setData(result);
    } catch {
      // API may not be connected
    } finally {
      setLoading(false);
    }
  }, [get, isAdmin, page, search, tierFilter]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  async function handleChangeTier(userId: string, newTier: string) {
    setActionLoading(userId);
    try {
      await put(`/api/admin/users/${userId}/tier`, { tier: newTier });
      await loadUsers();
    } catch {
      // Handle error
    } finally {
      setActionLoading(null);
    }
  }

  async function handleToggleSuspend(userId: string) {
    setActionLoading(userId);
    try {
      await put(`/api/admin/users/${userId}/suspend`);
      await loadUsers();
    } catch {
      // Handle error
    } finally {
      setActionLoading(null);
    }
  }

  if (!isAdmin) return null;

  const totalPages = data ? Math.ceil(data.total / data.per_page) : 0;

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-forest-dark">
          User Management
        </h1>
        <p className="mt-1 text-sm text-forest-dark/60">
          View and manage all platform users.
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="flex-1">
          <input
            type="text"
            placeholder="Search by email or name..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="w-full rounded-lg border border-mist bg-white px-4 py-2.5 text-sm text-forest-dark placeholder:text-forest-dark/40 focus:border-forest focus:outline-none focus:ring-1 focus:ring-forest"
          />
        </div>
        <select
          value={tierFilter}
          onChange={(e) => {
            setTierFilter(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-mist bg-white px-4 py-2.5 text-sm text-forest-dark focus:border-forest focus:outline-none focus:ring-1 focus:ring-forest"
        >
          <option value="all">All tiers</option>
          <option value="free">Free</option>
          <option value="basic">Basic</option>
          <option value="premium">Premium</option>
        </select>
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
      ) : !data || data.users.length === 0 ? (
        <div className="rounded-xl border border-mist bg-white p-8 text-center">
          <p className="text-sm text-forest-dark/60">No users found.</p>
        </div>
      ) : (
        <>
          <div className="rounded-xl border border-mist bg-white overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-mist">
                    <th className="px-5 py-3 text-left text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
                      Email
                    </th>
                    <th className="px-5 py-3 text-left text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
                      Name
                    </th>
                    <th className="px-5 py-3 text-left text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
                      Tier
                    </th>
                    <th className="px-5 py-3 text-left text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
                      Deployments
                    </th>
                    <th className="px-5 py-3 text-left text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
                      Compute Used
                    </th>
                    <th className="px-5 py-3 text-left text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
                      Last Active
                    </th>
                    <th className="px-5 py-3 text-left text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
                      Status
                    </th>
                    <th className="px-5 py-3 text-right text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-mist">
                  {data.users.map((u) => (
                    <tr
                      key={u.id}
                      className="hover:bg-sage/50 transition-colors"
                    >
                      <td className="px-5 py-4 text-sm font-medium text-forest-dark">
                        {u.email}
                      </td>
                      <td className="px-5 py-4 text-sm text-forest-dark/60">
                        {u.name || "--"}
                      </td>
                      <td className="px-5 py-4">
                        <TierBadge tier={u.tier} />
                      </td>
                      <td className="px-5 py-4 text-sm text-forest-dark/60">
                        {u.active_deployments}
                      </td>
                      <td className="px-5 py-4 text-sm text-forest-dark/60">
                        {u.compute_minutes_used} min
                      </td>
                      <td className="px-5 py-4 text-sm text-forest-dark/40">
                        {u.last_active_at
                          ? formatRelativeTime(u.last_active_at)
                          : "Never"}
                      </td>
                      <td className="px-5 py-4">
                        {u.is_suspended ? (
                          <span className="inline-flex items-center rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-medium text-red-600">
                            Suspended
                          </span>
                        ) : (
                          <span className="inline-flex items-center rounded-full bg-fern/10 px-2.5 py-0.5 text-xs font-medium text-fern">
                            Active
                          </span>
                        )}
                      </td>
                      <td className="px-5 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <select
                            value={u.tier}
                            onChange={(e) =>
                              handleChangeTier(u.id, e.target.value)
                            }
                            disabled={actionLoading === u.id}
                            className="rounded-md border border-mist bg-white px-2 py-1 text-xs text-forest-dark focus:border-forest focus:outline-none disabled:opacity-50"
                          >
                            <option value="free">Free</option>
                            <option value="basic">Basic</option>
                            <option value="premium">Premium</option>
                          </select>
                          <button
                            onClick={() => handleToggleSuspend(u.id)}
                            disabled={actionLoading === u.id}
                            className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors disabled:opacity-50 ${
                              u.is_suspended
                                ? "bg-fern/10 text-fern hover:bg-fern/20"
                                : "bg-red-50 text-red-600 hover:bg-red-100"
                            }`}
                          >
                            {u.is_suspended ? "Activate" : "Suspend"}
                          </button>
                        </div>
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
                {Math.min(page * 20, data.total)} of {data.total} users
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

function TierBadge({ tier }: { tier: string }) {
  const colors: Record<string, string> = {
    free: "bg-mist text-forest-dark/60",
    basic: "bg-forest/10 text-forest",
    premium: "bg-copper/10 text-copper",
  };

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${
        colors[tier] || "bg-mist text-forest-dark/60"
      }`}
    >
      {tier}
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
