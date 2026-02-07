/**
 * SSE stream consumer for AI chat responses.
 * Reads a ReadableStream and writes tokens to stdout in real-time.
 */
export async function consumeSSEStream(
  body: ReadableStream<Uint8Array>,
  onToken: (token: string) => void,
  onDone?: () => void,
): Promise<string> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let fullText = "";
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Process SSE events
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = line.slice(6);
        if (data === "[DONE]") {
          onDone?.();
          return fullText;
        }

        try {
          const parsed = JSON.parse(data);
          const content =
            parsed.choices?.[0]?.delta?.content ||
            parsed.choices?.[0]?.text ||
            parsed.content ||
            parsed.token ||
            "";
          if (content) {
            fullText += content;
            onToken(content);
          }
        } catch {
          // Not JSON — might be plain text token
          if (data.trim()) {
            fullText += data;
            onToken(data);
          }
        }
      }
    }
  }

  onDone?.();
  return fullText;
}
