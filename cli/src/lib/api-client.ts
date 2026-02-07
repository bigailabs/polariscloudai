import { PolarisApiError } from "./errors.js";
import { getApiKey, getApiUrl } from "./config-manager.js";
import type {
  HealthResponse,
  UserResponse,
  Template,
  Deployment,
  ApiKey,
  UsageAnalytics,
  DashboardStats,
  StorageVolume,
} from "./types.js";

export class PolarisClient {
  private baseUrl: string;
  private apiKey: string | null;

  constructor(baseUrl?: string, apiKey?: string) {
    this.baseUrl = (baseUrl || getApiUrl()).replace(/\/$/, "");
    this.apiKey = apiKey || getApiKey();
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown,
    requireAuth = true,
  ): Promise<T> {
    if (requireAuth && !this.apiKey) {
      throw new PolarisApiError(
        "Not authenticated",
        401,
        "No API key found. Run `polaris auth login` to authenticate.",
      );
    }

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "User-Agent": "polaris-cli/0.1.0",
    };

    if (this.apiKey) {
      headers["Authorization"] = `Bearer ${this.apiKey}`;
    }

    const url = `${this.baseUrl}${path}`;

    let res: Response;
    try {
      res = await fetch(url, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
      });
    } catch (err: any) {
      throw new PolarisApiError(
        "Connection failed",
        0,
        `Could not connect to ${this.baseUrl}. Is the API running?`,
      );
    }

    if (!res.ok) {
      let detail: string | undefined;
      try {
        const errBody = await res.json();
        detail = errBody.detail || errBody.message;
      } catch {}
      throw new PolarisApiError(
        `HTTP ${res.status}`,
        res.status,
        detail,
      );
    }

    return res.json() as Promise<T>;
  }

  // Health
  async health(): Promise<HealthResponse> {
    return this.request("GET", "/health", undefined, false);
  }

  // Auth
  async me(): Promise<UserResponse> {
    return this.request("GET", "/api/auth/me");
  }

  // Templates
  async listTemplates(): Promise<Record<string, Template>> {
    return this.request("GET", "/api/templates", undefined, false);
  }

  async getTemplate(id: string): Promise<Template> {
    return this.request("GET", `/api/templates/${id}`, undefined, false);
  }

  // Deployments
  async listDeployments(): Promise<{ deployments: Deployment[] }> {
    return this.request("GET", "/api/user/deployments");
  }

  async getDeployment(id: string): Promise<Deployment> {
    return this.request("GET", `/api/templates/deployments/${id}`);
  }

  async createDeployment(data: {
    template_id: string;
    name: string;
    parameters: Record<string, any>;
  }): Promise<any> {
    return this.request("POST", "/api/user/deployments", data);
  }

  async deleteDeployment(id: string): Promise<any> {
    return this.request("DELETE", `/api/user/deployments/${id}`);
  }

  // API Keys
  async listApiKeys(): Promise<{ keys: ApiKey[] }> {
    return this.request("GET", "/api/keys");
  }

  async generateApiKey(name: string, description?: string): Promise<{ success: boolean; key: ApiKey }> {
    return this.request("POST", "/api/keys/generate", { name, description });
  }

  async revokeApiKey(id: string): Promise<any> {
    return this.request("DELETE", `/api/keys/${id}`);
  }

  // Usage
  async getUsage(): Promise<UsageAnalytics> {
    return this.request("GET", "/api/usage");
  }

  // Dashboard stats
  async getStats(): Promise<DashboardStats> {
    return this.request("GET", "/api/stats");
  }

  // Storage
  async getUserStorage(): Promise<any> {
    return this.request("GET", "/api/user/storage");
  }

  // Raw request for streaming (AI chat)
  async rawFetch(
    method: string,
    path: string,
    body?: unknown,
  ): Promise<Response> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "User-Agent": "polaris-cli/0.1.0",
    };
    if (this.apiKey) {
      headers["Authorization"] = `Bearer ${this.apiKey}`;
    }
    return fetch(`${this.baseUrl}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  }
}

export function createClient(apiUrl?: string): PolarisClient {
  return new PolarisClient(apiUrl);
}
