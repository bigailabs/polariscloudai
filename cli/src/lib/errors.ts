export class PolarisApiError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public detail?: string,
  ) {
    super(message);
    this.name = "PolarisApiError";
  }

  toUserMessage(): string {
    switch (this.statusCode) {
      case 401:
        return "Not authenticated. Run `polaris auth login` to set your API key.";
      case 403:
        return "Permission denied. Your API key may not have access to this resource.";
      case 404:
        return this.detail || "Resource not found.";
      case 429:
        return "Rate limit exceeded. Please wait and try again.";
      case 500:
        return "Server error. The Polaris API may be experiencing issues.";
      default:
        return this.detail || this.message;
    }
  }
}

export class ConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ConfigError";
  }
}

export class AuthError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AuthError";
  }
}
