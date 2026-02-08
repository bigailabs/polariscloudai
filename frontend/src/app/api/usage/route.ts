import { auth } from "@clerk/nextjs/server";
import { NextRequest, NextResponse } from "next/server";
import { supabaseServer } from "@/lib/supabase-server";

export const runtime = "edge";

export async function GET(request: NextRequest) {
  const { userId } = await auth();
  if (!userId) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  // Get period from query param (default: current month)
  const { searchParams } = new URL(request.url);
  const period = searchParams.get("period"); // e.g. "2026-02"
  const now = new Date();
  const year = period ? parseInt(period.split("-")[0]) : now.getFullYear();
  const month = period ? parseInt(period.split("-")[1]) - 1 : now.getMonth();
  const startOfMonth = new Date(year, month, 1).toISOString();
  const endOfMonth = new Date(year, month + 1, 0, 23, 59, 59).toISOString();

  // Fetch raw usage records for this user in the period
  const { data: records, error } = await supabaseServer
    .from("inference_usage")
    .select("model, input_tokens, output_tokens, latency_ms, status_code, created_at")
    .eq("user_id", userId)
    .gte("created_at", startOfMonth)
    .lte("created_at", endOfMonth)
    .order("created_at", { ascending: false });

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  // Aggregate by model
  const byModel: Record<string, { requests: number; input_tokens: number; output_tokens: number }> = {};
  let totalRequests = 0;
  let totalInputTokens = 0;
  let totalOutputTokens = 0;
  let totalLatencyMs = 0;

  for (const r of records ?? []) {
    totalRequests++;
    totalInputTokens += r.input_tokens;
    totalOutputTokens += r.output_tokens;
    totalLatencyMs += r.latency_ms ?? 0;

    if (!byModel[r.model]) {
      byModel[r.model] = { requests: 0, input_tokens: 0, output_tokens: 0 };
    }
    byModel[r.model].requests++;
    byModel[r.model].input_tokens += r.input_tokens;
    byModel[r.model].output_tokens += r.output_tokens;
  }

  // Aggregate by day for chart
  const byDay: Record<string, number> = {};
  for (const r of records ?? []) {
    const day = r.created_at.slice(0, 10); // "2026-02-08"
    byDay[day] = (byDay[day] || 0) + 1;
  }

  const periodStr = `${year}-${String(month + 1).padStart(2, "0")}`;

  return NextResponse.json({
    period: periodStr,
    total_requests: totalRequests,
    total_input_tokens: totalInputTokens,
    total_output_tokens: totalOutputTokens,
    avg_latency_ms: totalRequests > 0 ? Math.round(totalLatencyMs / totalRequests) : 0,
    by_model: Object.entries(byModel).map(([model, stats]) => ({
      model,
      ...stats,
    })),
    by_day: Object.entries(byDay)
      .map(([date, requests]) => ({ date, requests }))
      .sort((a, b) => a.date.localeCompare(b.date)),
  });
}
