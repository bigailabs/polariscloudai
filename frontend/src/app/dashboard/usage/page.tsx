"use client";

import { useEffect, useState } from "react";
import { useApi } from "@/lib/hooks";

type ModelUsage = {
  model: string;
  requests: number;
  input_tokens: number;
  output_tokens: number;
};

type DayUsage = {
  date: string;
  requests: number;
};

type UsageData = {
  period: string;
  total_requests: number;
  total_input_tokens: number;
  total_output_tokens: number;
  avg_latency_ms: number;
  by_model: ModelUsage[];
  by_day: DayUsage[];
};

export default function UsagePage() {
  const { get } = useApi();
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await get<UsageData>("/api/usage");
        setUsage(data);
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
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-28 animate-pulse rounded-xl bg-white border border-mist" />
          ))}
        </div>
      </div>
    );
  }

  const maxDayRequests = Math.max(1, ...(usage?.by_day?.map((d) => d.requests) ?? [1]));

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-forest-dark">Usage</h1>
        <p className="mt-1 text-sm text-forest-dark/60">
          Inference API usage for {usage?.period ?? "this month"}.
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-4 mb-8">
        <div className="rounded-xl border border-mist bg-white p-5">
          <p className="text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
            Total requests
          </p>
          <p className="mt-2 text-2xl font-semibold text-forest-dark">
            {(usage?.total_requests ?? 0).toLocaleString()}
          </p>
        </div>
        <div className="rounded-xl border border-mist bg-white p-5">
          <p className="text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
            Input tokens
          </p>
          <p className="mt-2 text-2xl font-semibold text-forest-dark">
            {(usage?.total_input_tokens ?? 0).toLocaleString()}
          </p>
        </div>
        <div className="rounded-xl border border-mist bg-white p-5">
          <p className="text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
            Output tokens
          </p>
          <p className="mt-2 text-2xl font-semibold text-forest-dark">
            {(usage?.total_output_tokens ?? 0).toLocaleString()}
          </p>
        </div>
        <div className="rounded-xl border border-mist bg-white p-5">
          <p className="text-xs font-medium text-forest-dark/50 uppercase tracking-wide">
            Avg latency
          </p>
          <p className="mt-2 text-2xl font-semibold text-forest-dark">
            {usage?.avg_latency_ms ?? 0}ms
          </p>
        </div>
      </div>

      {/* Daily chart */}
      {usage && usage.by_day.length > 0 && (
        <div className="rounded-xl border border-mist bg-white p-5 mb-8">
          <h2 className="text-sm font-semibold text-forest-dark mb-4">
            Requests per day
          </h2>
          <div className="flex items-end gap-1 h-32">
            {usage.by_day.map((day) => (
              <div key={day.date} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className="w-full rounded-t bg-forest/80 hover:bg-forest transition-colors min-h-[2px]"
                  style={{ height: `${(day.requests / maxDayRequests) * 100}%` }}
                  title={`${day.date}: ${day.requests} requests`}
                />
                <span className="text-[10px] text-forest-dark/40 font-mono">
                  {day.date.slice(8)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Model breakdown */}
      {usage && usage.by_model.length > 0 ? (
        <div className="rounded-xl border border-mist bg-white p-5">
          <h2 className="text-sm font-semibold text-forest-dark mb-4">
            Usage by model
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-mist">
                  <th className="pb-3 text-left font-medium text-forest-dark/50">Model</th>
                  <th className="pb-3 text-right font-medium text-forest-dark/50">Requests</th>
                  <th className="pb-3 text-right font-medium text-forest-dark/50">Input tokens</th>
                  <th className="pb-3 text-right font-medium text-forest-dark/50">Output tokens</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-mist">
                {usage.by_model.map((m) => (
                  <tr key={m.model}>
                    <td className="py-3 text-forest-dark font-mono text-xs">{m.model}</td>
                    <td className="py-3 text-right text-forest-dark font-mono">
                      {m.requests.toLocaleString()}
                    </td>
                    <td className="py-3 text-right text-forest-dark/60 font-mono">
                      {m.input_tokens.toLocaleString()}
                    </td>
                    <td className="py-3 text-right text-forest-dark/60 font-mono">
                      {m.output_tokens.toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t border-forest-dark/10">
                  <td className="pt-3 font-medium text-forest-dark">Total</td>
                  <td className="pt-3 text-right font-medium text-forest-dark font-mono">
                    {usage.total_requests.toLocaleString()}
                  </td>
                  <td className="pt-3 text-right font-medium text-forest-dark/60 font-mono">
                    {usage.total_input_tokens.toLocaleString()}
                  </td>
                  <td className="pt-3 text-right font-medium text-forest-dark/60 font-mono">
                    {usage.total_output_tokens.toLocaleString()}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-mist bg-white p-8 text-center">
          <p className="text-sm text-forest-dark/60">
            No usage data yet. Make your first API call to see stats here.
          </p>
        </div>
      )}
    </div>
  );
}
