const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getWsUrl(): string {
  const url = new URL(API_URL);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString().replace(/\/$/, "");
}

export type DeploymentMessage = {
  deployment_id: string;
  message?: string;
  status?: string;
  timestamp?: string;
  type?: string;
  progress?: number;
  error?: string;
};

type MessageHandler = (msg: DeploymentMessage) => void;

export function connectDeploymentWs(
  deploymentId: string,
  token: string,
  onMessage: MessageHandler,
  onClose?: (code: number, reason: string) => void
): WebSocket {
  const wsUrl = `${getWsUrl()}/ws/deployments/${deploymentId}?token=${encodeURIComponent(token)}`;
  const ws = new WebSocket(wsUrl);

  ws.onmessage = (event) => {
    try {
      const data: DeploymentMessage = JSON.parse(event.data);
      onMessage(data);
    } catch {
      // ignore non-JSON messages
    }
  };

  ws.onclose = (event) => {
    onClose?.(event.code, event.reason);
  };

  return ws;
}
