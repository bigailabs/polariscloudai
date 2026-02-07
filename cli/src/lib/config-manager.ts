import * as fs from "node:fs";
import * as path from "node:path";
import * as os from "node:os";
import type { PolarisConfig } from "./types.js";

const POLARIS_DIR = path.join(os.homedir(), ".polaris");
const CONFIG_FILE = path.join(POLARIS_DIR, "config.json");
const CREDENTIALS_FILE = path.join(POLARIS_DIR, "credentials");

const DEFAULT_CONFIG: PolarisConfig = {
  apiUrl: "https://api.polaris.computer",
  defaultFormat: "table",
  noColor: false,
};

function ensureDir() {
  if (!fs.existsSync(POLARIS_DIR)) {
    fs.mkdirSync(POLARIS_DIR, { recursive: true, mode: 0o700 });
  }
}

// --- Config ---

export function loadConfig(): PolarisConfig {
  ensureDir();
  if (!fs.existsSync(CONFIG_FILE)) {
    return { ...DEFAULT_CONFIG };
  }
  try {
    const raw = fs.readFileSync(CONFIG_FILE, "utf-8");
    return { ...DEFAULT_CONFIG, ...JSON.parse(raw) };
  } catch {
    return { ...DEFAULT_CONFIG };
  }
}

export function saveConfig(config: PolarisConfig) {
  ensureDir();
  fs.writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2), {
    mode: 0o600,
  });
}

export function getConfigValue(key: string): string | undefined {
  const config: Record<string, unknown> = { ...loadConfig() };
  const val = config[key];
  return val !== undefined ? String(val) : undefined;
}

export function setConfigValue(key: string, value: string) {
  const config: Record<string, unknown> = { ...loadConfig() };
  // Coerce booleans
  if (value === "true") config[key] = true;
  else if (value === "false") config[key] = false;
  else config[key] = value;
  saveConfig(config as unknown as PolarisConfig);
}

export function resetConfig() {
  saveConfig({ ...DEFAULT_CONFIG });
}

// --- Credentials ---

export function getApiKey(): string | null {
  ensureDir();
  if (!fs.existsSync(CREDENTIALS_FILE)) {
    return null;
  }
  try {
    const content = fs.readFileSync(CREDENTIALS_FILE, "utf-8").trim();
    // Format: api_key=<key>
    for (const line of content.split("\n")) {
      const trimmed = line.trim();
      if (trimmed.startsWith("api_key=")) {
        return trimmed.slice("api_key=".length);
      }
    }
    return null;
  } catch {
    return null;
  }
}

export function saveApiKey(apiKey: string) {
  ensureDir();
  fs.writeFileSync(CREDENTIALS_FILE, `api_key=${apiKey}\n`, { mode: 0o600 });
}

export function removeCredentials() {
  if (fs.existsSync(CREDENTIALS_FILE)) {
    fs.unlinkSync(CREDENTIALS_FILE);
  }
}

export function getApiUrl(): string {
  return loadConfig().apiUrl;
}
