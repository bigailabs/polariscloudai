import { NextRequest, NextResponse } from "next/server";
import { validateApiKey, recordKeyUsageDirect } from "@/lib/auth-api-key";
import { resolveModel } from "@/lib/models";
import { supabaseServer } from "@/lib/supabase-server";

export const runtime = "edge";

const GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions";

export async function POST(request: NextRequest) {
  // --- Auth ---
  const authHeader = request.headers.get("authorization");
  if (!authHeader?.startsWith("Bearer ")) {
    return NextResponse.json(
      { error: { message: "Missing API key. Include Authorization: Bearer pi_sk_...", type: "auth_error", code: "missing_api_key" } },
      { status: 401 }
    );
  }

  const rawKey = authHeader.slice(7);
  const keyRecord = await validateApiKey(rawKey);
  if (!keyRecord) {
    return NextResponse.json(
      { error: { message: "Invalid or revoked API key.", type: "auth_error", code: "invalid_api_key" } },
      { status: 401 }
    );
  }

  // --- Parse body ---
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { error: { message: "Invalid JSON in request body.", type: "invalid_request", code: "parse_error" } },
      { status: 400 }
    );
  }

  const requestedModel = body.model as string | undefined;
  if (!requestedModel) {
    return NextResponse.json(
      { error: { message: "Missing 'model' field.", type: "invalid_request", code: "missing_model" } },
      { status: 400 }
    );
  }

  // --- Resolve model ---
  const modelInfo = resolveModel(requestedModel);
  if (!modelInfo) {
    return NextResponse.json(
      {
        error: {
          message: `Unknown model '${requestedModel}'. Use GET /v1/models to see available models.`,
          type: "invalid_request",
          code: "unknown_model",
        },
      },
      { status: 400 }
    );
  }

  // --- Proxy to Groq ---
  const groqApiKey = process.env.GROQ_API_KEY;
  if (!groqApiKey) {
    return NextResponse.json(
      { error: { message: "Inference backend not configured.", type: "server_error", code: "no_backend" } },
      { status: 503 }
    );
  }

  const isStreaming = body.stream === true;
  const startTime = Date.now();

  const groqBody = { ...body, model: modelInfo.groq_id };

  const groqResponse = await fetch(GROQ_API_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${groqApiKey}`,
    },
    body: JSON.stringify(groqBody),
  });

  if (!groqResponse.ok) {
    const latencyMs = Date.now() - startTime;
    const errorText = await groqResponse.text();

    // Log failed usage
    await logUsage(keyRecord.id, keyRecord.user_id, requestedModel, 0, 0, latencyMs, groqResponse.status);
    await recordKeyUsageDirect(keyRecord.id);

    let errorJson;
    try {
      errorJson = JSON.parse(errorText);
    } catch {
      errorJson = { error: { message: errorText } };
    }

    return NextResponse.json(errorJson, { status: groqResponse.status });
  }

  // --- Streaming response ---
  if (isStreaming) {
    // Record usage (we won't have token counts for streaming)
    recordKeyUsageDirect(keyRecord.id).catch(() => {});

    const groqStream = groqResponse.body;
    if (!groqStream) {
      return NextResponse.json(
        { error: { message: "No response stream from backend.", type: "server_error" } },
        { status: 502 }
      );
    }

    // Transform stream: rewrite model ID back to Polaris ID
    const transform = new TransformStream({
      transform(chunk, controller) {
        const text = new TextDecoder().decode(chunk);
        const rewritten = text.replaceAll(modelInfo.groq_id, requestedModel);
        controller.enqueue(new TextEncoder().encode(rewritten));
      },
    });

    const transformedStream = groqStream.pipeThrough(transform);

    return new Response(transformedStream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  }

  // --- Non-streaming response ---
  const groqData = await groqResponse.json();
  const latencyMs = Date.now() - startTime;

  // Rewrite model ID
  groqData.model = requestedModel;

  // Log usage
  const inputTokens = groqData.usage?.prompt_tokens ?? 0;
  const outputTokens = groqData.usage?.completion_tokens ?? 0;
  await logUsage(keyRecord.id, keyRecord.user_id, requestedModel, inputTokens, outputTokens, latencyMs, 200);
  await recordKeyUsageDirect(keyRecord.id);

  return NextResponse.json(groqData);
}

async function logUsage(
  apiKeyId: string,
  userId: string,
  model: string,
  inputTokens: number,
  outputTokens: number,
  latencyMs: number,
  statusCode: number
): Promise<void> {
  try {
    await supabaseServer.from("inference_usage").insert({
      api_key_id: apiKeyId,
      user_id: userId,
      model,
      input_tokens: inputTokens,
      output_tokens: outputTokens,
      latency_ms: latencyMs,
      status_code: statusCode,
    });
  } catch {
    // Don't fail the request if logging fails
  }
}
