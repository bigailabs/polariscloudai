export const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

/**
 * Returns true when backend API calls should work.
 * In production (no NEXT_PUBLIC_API_URL), requests go to the same origin
 * via Next.js route handlers, so the backend is always configured.
 * On localhost, we need an explicit API_URL.
 */
export function isBackendConfigured(): boolean {
  // In production, Next.js route handlers ARE the backend
  if (typeof window !== "undefined" && window.location.hostname !== "localhost") {
    return true;
  }
  // On localhost, need an explicit URL (either FastAPI or local next dev)
  return !!API_URL;
}

type FetchOptions = RequestInit & {
  token?: string | null;
};

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  async request<T = unknown>(
    path: string,
    options: FetchOptions = {}
  ): Promise<T> {
    if (!isBackendConfigured()) {
      throw new ApiError(0, "Backend not configured");
    }

    const { token, ...fetchOptions } = options;

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(fetchOptions.headers as Record<string, string>),
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      ...fetchOptions,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: response.statusText,
      }));
      throw new ApiError(response.status, error.detail || "Request failed");
    }

    return response.json();
  }

  async get<T = unknown>(path: string, token?: string | null): Promise<T> {
    return this.request<T>(path, { method: "GET", token });
  }

  async post<T = unknown>(
    path: string,
    body?: unknown,
    token?: string | null
  ): Promise<T> {
    return this.request<T>(path, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
      token,
    });
  }

  async put<T = unknown>(
    path: string,
    body?: unknown,
    token?: string | null
  ): Promise<T> {
    return this.request<T>(path, {
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
      token,
    });
  }

  async delete<T = unknown>(path: string, token?: string | null): Promise<T> {
    return this.request<T>(path, { method: "DELETE", token });
  }
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

export const api = new ApiClient(API_URL);
