import { NextResponse } from "next/server";
import { MODELS } from "@/lib/models";

export const runtime = "edge";

export async function GET() {
  const data = MODELS.map((m) => ({
    id: m.id,
    object: "model",
    created: 1700000000,
    owned_by: m.owned_by,
    context_window: m.context_window,
  }));

  return NextResponse.json({
    object: "list",
    data,
  });
}
