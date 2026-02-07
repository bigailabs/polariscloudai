#!/usr/bin/env node
"use strict";
var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));

// src/index.ts
var import_commander = require("commander");

// src/lib/branding.ts
var import_chalk = __toESM(require("chalk"));
var POLARIS_ASCII = `
  ____       _            _
 |  _ \\ ___ | | __ _ _ __(_)___
 | |_) / _ \\| |/ _\` | '__| / __|
 |  __/ (_) | | (_| | |  | \\__ \\
 |_|   \\___/|_|\\__,_|_|  |_|___/
`;
function printBanner() {
  console.log(import_chalk.default.hex("#2D5A47")(POLARIS_ASCII));
  console.log(
    import_chalk.default.dim("  Polaris Cloud CLI \u2014 GPU compute at your fingertips\n")
  );
}

// src/commands/auth.ts
var import_prompts = require("@inquirer/prompts");
var import_chalk3 = __toESM(require("chalk"));

// src/lib/errors.ts
var PolarisApiError = class extends Error {
  constructor(message, statusCode, detail) {
    super(message);
    this.statusCode = statusCode;
    this.detail = detail;
    this.name = "PolarisApiError";
  }
  toUserMessage() {
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
};

// src/lib/config-manager.ts
var fs = __toESM(require("fs"));
var path = __toESM(require("path"));
var os = __toESM(require("os"));
var POLARIS_DIR = path.join(os.homedir(), ".polaris");
var CONFIG_FILE = path.join(POLARIS_DIR, "config.json");
var CREDENTIALS_FILE = path.join(POLARIS_DIR, "credentials");
var DEFAULT_CONFIG = {
  apiUrl: "https://api.polaris.computer",
  defaultFormat: "table",
  noColor: false
};
function ensureDir() {
  if (!fs.existsSync(POLARIS_DIR)) {
    fs.mkdirSync(POLARIS_DIR, { recursive: true, mode: 448 });
  }
}
function loadConfig() {
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
function saveConfig(config) {
  ensureDir();
  fs.writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2), {
    mode: 384
  });
}
function getConfigValue(key) {
  const config = { ...loadConfig() };
  const val = config[key];
  return val !== void 0 ? String(val) : void 0;
}
function setConfigValue(key, value) {
  const config = { ...loadConfig() };
  if (value === "true") config[key] = true;
  else if (value === "false") config[key] = false;
  else config[key] = value;
  saveConfig(config);
}
function resetConfig() {
  saveConfig({ ...DEFAULT_CONFIG });
}
function getApiKey() {
  ensureDir();
  if (!fs.existsSync(CREDENTIALS_FILE)) {
    return null;
  }
  try {
    const content = fs.readFileSync(CREDENTIALS_FILE, "utf-8").trim();
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
function saveApiKey(apiKey) {
  ensureDir();
  fs.writeFileSync(CREDENTIALS_FILE, `api_key=${apiKey}
`, { mode: 384 });
}
function removeCredentials() {
  if (fs.existsSync(CREDENTIALS_FILE)) {
    fs.unlinkSync(CREDENTIALS_FILE);
  }
}
function getApiUrl() {
  return loadConfig().apiUrl;
}

// src/lib/api-client.ts
var PolarisClient = class {
  baseUrl;
  apiKey;
  constructor(baseUrl, apiKey) {
    this.baseUrl = (baseUrl || getApiUrl()).replace(/\/$/, "");
    this.apiKey = apiKey || getApiKey();
  }
  async request(method, path3, body, requireAuth = true) {
    if (requireAuth && !this.apiKey) {
      throw new PolarisApiError(
        "Not authenticated",
        401,
        "No API key found. Run `polaris auth login` to authenticate."
      );
    }
    const headers = {
      "Content-Type": "application/json",
      "User-Agent": "polaris-cli/0.1.0"
    };
    if (this.apiKey) {
      headers["Authorization"] = `Bearer ${this.apiKey}`;
    }
    const url = `${this.baseUrl}${path3}`;
    let res;
    try {
      res = await fetch(url, {
        method,
        headers,
        body: body ? JSON.stringify(body) : void 0
      });
    } catch (err) {
      throw new PolarisApiError(
        "Connection failed",
        0,
        `Could not connect to ${this.baseUrl}. Is the API running?`
      );
    }
    if (!res.ok) {
      let detail;
      try {
        const errBody = await res.json();
        detail = errBody.detail || errBody.message;
      } catch {
      }
      throw new PolarisApiError(
        `HTTP ${res.status}`,
        res.status,
        detail
      );
    }
    return res.json();
  }
  // Health
  async health() {
    return this.request("GET", "/health", void 0, false);
  }
  // Auth
  async me() {
    return this.request("GET", "/api/auth/me");
  }
  // Templates
  async listTemplates() {
    return this.request("GET", "/api/templates", void 0, false);
  }
  async getTemplate(id) {
    return this.request("GET", `/api/templates/${id}`, void 0, false);
  }
  // Deployments
  async listDeployments() {
    return this.request("GET", "/api/user/deployments");
  }
  async getDeployment(id) {
    return this.request("GET", `/api/templates/deployments/${id}`);
  }
  async createDeployment(data) {
    return this.request("POST", "/api/user/deployments", data);
  }
  async deleteDeployment(id) {
    return this.request("DELETE", `/api/user/deployments/${id}`);
  }
  // API Keys
  async listApiKeys() {
    return this.request("GET", "/api/keys");
  }
  async generateApiKey(name, description) {
    return this.request("POST", "/api/keys/generate", { name, description });
  }
  async revokeApiKey(id) {
    return this.request("DELETE", `/api/keys/${id}`);
  }
  // Usage
  async getUsage() {
    return this.request("GET", "/api/usage");
  }
  // Dashboard stats
  async getStats() {
    return this.request("GET", "/api/stats");
  }
  // Storage
  async getUserStorage() {
    return this.request("GET", "/api/user/storage");
  }
  // Raw request for streaming (AI chat)
  async rawFetch(method, path3, body) {
    const headers = {
      "Content-Type": "application/json",
      "User-Agent": "polaris-cli/0.1.0"
    };
    if (this.apiKey) {
      headers["Authorization"] = `Bearer ${this.apiKey}`;
    }
    return fetch(`${this.baseUrl}${path3}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : void 0
    });
  }
};
function createClient(apiUrl) {
  return new PolarisClient(apiUrl);
}

// src/lib/output.ts
var import_chalk2 = __toESM(require("chalk"));
var import_cli_table3 = __toESM(require("cli-table3"));
var forest = import_chalk2.default.hex("#2D5A47");
var fern = import_chalk2.default.hex("#4A7C59");
var copper = import_chalk2.default.hex("#B87333");
function printSuccess(message) {
  console.log(fern("\u2713") + " " + message);
}
function printError(message) {
  console.error(import_chalk2.default.red("\u2717") + " " + message);
}
function printInfo(message) {
  console.log(import_chalk2.default.dim("\u2192") + " " + message);
}
function printKeyValue(pairs) {
  const maxKeyLen = Math.max(...Object.keys(pairs).map((k) => k.length));
  for (const [key, value] of Object.entries(pairs)) {
    const paddedKey = key.padEnd(maxKeyLen);
    console.log(`  ${import_chalk2.default.dim(paddedKey)}  ${value ?? import_chalk2.default.dim("\u2014")}`);
  }
}
function printTable(headers, rows) {
  const table = new import_cli_table3.default({
    head: headers.map((h) => forest(h)),
    style: { head: [], border: ["dim"] },
    chars: {
      top: "\u2500",
      "top-mid": "\u252C",
      "top-left": "\u250C",
      "top-right": "\u2510",
      bottom: "\u2500",
      "bottom-mid": "\u2534",
      "bottom-left": "\u2514",
      "bottom-right": "\u2518",
      left: "\u2502",
      "left-mid": "\u251C",
      mid: "\u2500",
      "mid-mid": "\u253C",
      right: "\u2502",
      "right-mid": "\u2524",
      middle: "\u2502"
    }
  });
  for (const row of rows) {
    table.push(row.map(String));
  }
  console.log(table.toString());
}
function printJson(data) {
  console.log(JSON.stringify(data, null, 2));
}

// src/lib/spinner.ts
var import_ora = __toESM(require("ora"));
function createSpinner(text) {
  return (0, import_ora.default)({ text, color: "green" });
}

// src/commands/auth.ts
function registerAuthCommand(program2) {
  const auth = program2.command("auth").description("Manage authentication");
  auth.command("login").description("Authenticate with your API key").option("--key <key>", "API key (or enter interactively)").action(async (opts) => {
    const json = program2.opts().json;
    let apiKey = opts.key;
    if (!apiKey) {
      console.log(
        import_chalk3.default.dim("Get your API key from the dashboard: ") + import_chalk3.default.underline("https://polaris.computer/dashboard/api-keys")
      );
      console.log();
      apiKey = await (0, import_prompts.password)({
        message: "Enter your API key:",
        mask: "*"
      });
    }
    if (!apiKey || !apiKey.trim()) {
      printError("No API key provided.");
      process.exit(1);
    }
    apiKey = apiKey.trim();
    const spinner = createSpinner("Validating API key...");
    spinner.start();
    try {
      const client = new PolarisClient(void 0, apiKey);
      const user = await client.me();
      spinner.stop();
      saveApiKey(apiKey);
      if (json) {
        printJson({ success: true, user });
      } else {
        printSuccess("Authenticated successfully!");
        console.log();
        printKeyValue({
          Email: user.email,
          Name: user.name || "\u2014",
          Tier: user.tier
        });
      }
    } catch (err) {
      spinner.stop();
      if (err instanceof PolarisApiError && err.statusCode === 401) {
        printError("Invalid API key. Please check and try again.");
      } else if (err instanceof PolarisApiError && err.statusCode === 0) {
        saveApiKey(apiKey);
        printSuccess("API key saved (could not verify \u2014 API unreachable).");
      } else {
        printError(
          err instanceof PolarisApiError ? err.toUserMessage() : String(err)
        );
      }
      process.exit(1);
    }
  });
  auth.command("logout").description("Remove stored credentials").action(async () => {
    const json = program2.opts().json;
    removeCredentials();
    if (json) {
      printJson({ success: true });
    } else {
      printSuccess("Logged out. Credentials removed.");
    }
  });
  auth.command("status").description("Show current authentication status").action(async () => {
    const json = program2.opts().json;
    const apiKey = getApiKey();
    if (!apiKey) {
      if (json) {
        printJson({ authenticated: false });
      } else {
        printError("Not authenticated. Run `polaris auth login` to sign in.");
      }
      return;
    }
    const spinner = createSpinner("Checking authentication...");
    spinner.start();
    try {
      const client = createClient(program2.opts().apiUrl);
      const user = await client.me();
      spinner.stop();
      if (json) {
        printJson({ authenticated: true, user });
      } else {
        printSuccess("Authenticated");
        console.log();
        printKeyValue({
          Email: user.email,
          Name: user.name || "\u2014",
          Tier: user.tier,
          "API Key": apiKey.slice(0, 12) + "..." + apiKey.slice(-4)
        });
      }
    } catch (err) {
      spinner.stop();
      if (json) {
        printJson({ authenticated: false, error: String(err) });
      } else {
        printError(
          err instanceof PolarisApiError ? err.toUserMessage() : `Auth check failed: ${err}`
        );
      }
    }
  });
}

// src/commands/health.ts
var import_chalk4 = __toESM(require("chalk"));
function registerHealthCommand(program2) {
  program2.command("health").description("Check Polaris Cloud API status").action(async () => {
    const json = program2.opts().json;
    const spinner = createSpinner("Checking API status...");
    spinner.start();
    try {
      const client = createClient(program2.opts().apiUrl);
      const health = await client.health();
      spinner.stop();
      if (json) {
        printJson(health);
      } else {
        const statusIcon = health.status === "healthy" ? import_chalk4.default.green("\u25CF") : import_chalk4.default.red("\u25CF");
        console.log(`${statusIcon} ${health.service} v${health.version}`);
        console.log();
        printKeyValue({
          Status: health.status,
          Database: health.database,
          "Demo Mode": health.demo_mode ? "yes" : "no",
          Auth: health.auth_enabled ? "enabled" : "disabled"
        });
      }
    } catch (err) {
      spinner.stop();
      if (json) {
        printJson({
          status: "unreachable",
          error: err instanceof PolarisApiError ? err.detail : String(err)
        });
      } else {
        printError(
          err instanceof PolarisApiError ? err.toUserMessage() : `Could not reach API: ${err}`
        );
      }
      process.exit(1);
    }
  });
}

// src/commands/config.ts
function registerConfigCommand(program2) {
  const config = program2.command("config").description("Manage CLI configuration");
  config.command("get <key>").description("Get a config value").action((key) => {
    const json = program2.opts().json;
    const value = getConfigValue(key);
    if (value === void 0) {
      if (json) {
        printJson({ key, value: null });
      } else {
        printError(`Unknown config key: ${key}`);
      }
      return;
    }
    if (json) {
      printJson({ key, value });
    } else {
      console.log(value);
    }
  });
  config.command("set <key> <value>").description("Set a config value").action((key, value) => {
    const json = program2.opts().json;
    setConfigValue(key, value);
    if (json) {
      printJson({ success: true, key, value });
    } else {
      printSuccess(`Set ${key} = ${value}`);
    }
  });
  config.command("list").description("Show all config values").action(() => {
    const json = program2.opts().json;
    const cfg = loadConfig();
    if (json) {
      printJson(cfg);
    } else {
      printKeyValue(cfg);
    }
  });
  config.command("reset").description("Reset config to defaults").action(() => {
    const json = program2.opts().json;
    resetConfig();
    if (json) {
      printJson({ success: true });
    } else {
      printSuccess("Config reset to defaults.");
    }
  });
}

// src/commands/compute.ts
var import_chalk5 = __toESM(require("chalk"));
function registerComputeCommand(program2) {
  const compute = program2.command("compute").description("Browse available compute resources and templates");
  compute.command("templates").description("List available deployment templates").action(async () => {
    const json = program2.opts().json;
    const spinner = createSpinner("Fetching templates...");
    spinner.start();
    try {
      const client = createClient(program2.opts().apiUrl);
      const templates = await client.listTemplates();
      spinner.stop();
      if (json) {
        printJson(templates);
        return;
      }
      const rows = Object.values(templates).map((t) => [
        t.icon + " " + t.id,
        t.name,
        t.category,
        t.estimated_deploy_time,
        t.access_type
      ]);
      printTable(
        ["ID", "Name", "Category", "Deploy Time", "Access"],
        rows
      );
    } catch (err) {
      spinner.stop();
      printError(
        err instanceof PolarisApiError ? err.toUserMessage() : String(err)
      );
      process.exit(1);
    }
  });
  compute.command("get <templateId>").description("Show template details").action(async (templateId) => {
    const json = program2.opts().json;
    const spinner = createSpinner("Fetching template...");
    spinner.start();
    try {
      const client = createClient(program2.opts().apiUrl);
      const template = await client.getTemplate(templateId);
      spinner.stop();
      if (json) {
        printJson(template);
        return;
      }
      console.log(
        `
${template.icon} ${import_chalk5.default.bold(template.name)}
`
      );
      printKeyValue({
        ID: template.id,
        Category: template.category,
        "Deploy Time": template.estimated_deploy_time,
        Access: template.access_type,
        Port: String(template.default_port)
      });
      console.log(`
${import_chalk5.default.dim("Description:")} ${template.description}`);
      console.log(
        `
${import_chalk5.default.dim("Features:")}
${template.features.map((f) => `  \u2022 ${f}`).join("\n")}`
      );
      if (template.parameters.length > 0) {
        console.log(`
${import_chalk5.default.dim("Parameters:")}`);
        for (const p of template.parameters) {
          const req = p.required ? import_chalk5.default.red("*") : "";
          const def = p.default !== void 0 ? import_chalk5.default.dim(` (default: ${p.default})`) : "";
          console.log(`  ${p.name}${req} \u2014 ${p.label}${def}`);
        }
      }
    } catch (err) {
      spinner.stop();
      printError(
        err instanceof PolarisApiError ? err.toUserMessage() : String(err)
      );
      process.exit(1);
    }
  });
  compute.command("pricing").description("Show GPU pricing reference").action(async () => {
    const json = program2.opts().json;
    const pricing = [
      ["RTX 3060", "12 GB", "$0.25/hr", "$150/mo"],
      ["RTX 3080", "10 GB", "$0.45/hr", "$270/mo"],
      ["RTX 3090", "24 GB", "$0.55/hr", "$330/mo"],
      ["RTX 4070", "12 GB", "$0.40/hr", "$240/mo"],
      ["RTX 4080", "16 GB", "$0.65/hr", "$390/mo"],
      ["RTX 4090", "24 GB", "$0.85/hr", "$510/mo"],
      ["A100 40GB", "40 GB", "$1.50/hr", "$900/mo"],
      ["A100 80GB", "80 GB", "$2.00/hr", "$1200/mo"],
      ["H100", "80 GB", "$3.50/hr", "$2100/mo"]
    ];
    if (json) {
      printJson(
        pricing.map(([gpu, vram, hourly, monthly]) => ({
          gpu,
          vram,
          hourly,
          monthly
        }))
      );
      return;
    }
    printTable(["GPU", "VRAM", "Hourly", "Monthly"], pricing);
    console.log(
      import_chalk5.default.dim("\n  Prices are estimates. Actual pricing depends on availability.\n")
    );
  });
  compute.command("regions").description("List available regions").action(async () => {
    const json = program2.opts().json;
    const regions = [
      ["lagos", "Lagos, Nigeria", "\u25CF", "Verda"],
      ["helsinki", "Helsinki, Finland", "\u25CF", "Hetzner"]
    ];
    if (json) {
      printJson(
        regions.map(([id, name, status, provider]) => ({
          id,
          name,
          status: "available",
          provider
        }))
      );
      return;
    }
    printTable(
      ["Region", "Location", "Status", "Provider"],
      regions.map(([id, name, _status, provider]) => [
        id,
        name,
        import_chalk5.default.green("\u25CF available"),
        provider
      ])
    );
  });
}

// src/commands/deploy.ts
var import_chalk6 = __toESM(require("chalk"));

// src/lib/prompts.ts
var import_prompts2 = require("@inquirer/prompts");

// src/commands/deploy.ts
function registerDeployCommand(program2) {
  program2.command("deploy").description("Deploy a new instance (interactive or with flags)").option("--template <id>", "Template ID (e.g., ollama, jupyter)").option("--name <name>", "Deployment name").option("--gpu <type>", "GPU type filter (for display only)").option("--region <region>", "Region (for display only)").option("-y, --yes", "Skip confirmation").action(async (opts) => {
    const json = program2.opts().json;
    try {
      const client = createClient(program2.opts().apiUrl);
      const spinner = createSpinner("Loading templates...");
      spinner.start();
      const templates = await client.listTemplates();
      spinner.stop();
      const templateList = Object.values(templates);
      if (templateList.length === 0) {
        printError("No templates available.");
        process.exit(1);
      }
      let templateId = opts.template;
      if (!templateId) {
        templateId = await (0, import_prompts2.select)({
          message: "Select a template to deploy:",
          choices: templateList.map((t) => ({
            name: `${t.icon} ${t.name} \u2014 ${t.description.slice(0, 60)}...`,
            value: t.id
          }))
        });
      }
      const template = templates[templateId];
      if (!template) {
        printError(`Template "${templateId}" not found.`);
        process.exit(1);
      }
      let name = opts.name;
      if (!name) {
        name = await (0, import_prompts2.input)({
          message: "Deployment name:",
          default: `${template.id}-${Date.now().toString(36).slice(-4)}`,
          validate: (v) => /^[a-zA-Z0-9_-]+$/.test(v) || "Only letters, numbers, hyphens, underscores"
        });
      }
      const params = {};
      for (const param of template.parameters) {
        if (param.options && param.options.length > 0) {
          params[param.name] = await (0, import_prompts2.select)({
            message: `${param.label}:`,
            choices: param.options.map((o) => ({
              name: o.label,
              value: o.value
            })),
            default: param.default
          });
        } else if (param.type === "number") {
          const val = await (0, import_prompts2.input)({
            message: `${param.label}:`,
            default: param.default !== void 0 ? String(param.default) : void 0
          });
          params[param.name] = parseInt(val, 10);
        } else {
          params[param.name] = await (0, import_prompts2.input)({
            message: `${param.label}:`,
            default: param.default !== void 0 ? String(param.default) : void 0
          });
        }
      }
      if (!opts.yes) {
        console.log();
        console.log(
          import_chalk6.default.bold(`  ${template.icon} Deploying ${template.name}`)
        );
        printKeyValue({
          Template: template.id,
          Name: name,
          "Deploy Time": template.estimated_deploy_time,
          Access: template.access_type,
          ...Object.fromEntries(
            Object.entries(params).map(([k, v]) => [k, String(v)])
          )
        });
        console.log();
        const ok = await (0, import_prompts2.confirm)({
          message: "Deploy now?",
          default: true
        });
        if (!ok) {
          printInfo("Cancelled.");
          return;
        }
      }
      const deploySpinner = createSpinner(
        `Deploying ${template.name}...`
      );
      deploySpinner.start();
      const result = await client.createDeployment({
        template_id: templateId,
        name,
        parameters: params
      });
      deploySpinner.stop();
      if (json) {
        printJson(result);
        return;
      }
      printSuccess(`Deployment created!`);
      console.log();
      if (result.deployment_id) {
        printKeyValue({
          "Deployment ID": result.deployment_id,
          Status: result.status || "pending"
        });
      }
      if (result.access_url) {
        console.log();
        printInfo(`Access URL: ${import_chalk6.default.underline(result.access_url)}`);
      }
      console.log();
      printInfo(
        `Track progress: ${import_chalk6.default.dim("polaris instances get " + (result.deployment_id || name))}`
      );
    } catch (err) {
      printError(
        err instanceof PolarisApiError ? err.toUserMessage() : String(err)
      );
      process.exit(1);
    }
  });
}

// src/commands/instances.ts
var import_node_child_process = require("child_process");
var import_chalk7 = __toESM(require("chalk"));
var STATUS_COLORS = {
  running: import_chalk7.default.green,
  pending: import_chalk7.default.yellow,
  warming: import_chalk7.default.yellow,
  provisioning: import_chalk7.default.yellow,
  installing: import_chalk7.default.cyan,
  stopping: import_chalk7.default.gray,
  stopped: import_chalk7.default.gray,
  failed: import_chalk7.default.red
};
function colorStatus(status) {
  const colorFn = STATUS_COLORS[status] || import_chalk7.default.white;
  return colorFn(status);
}
function registerInstancesCommand(program2) {
  const instances = program2.command("instances").description("Manage your running deployments");
  instances.command("list").alias("ls").description("List your deployments").option("--status <status>", "Filter by status").action(async (opts) => {
    const json = program2.opts().json;
    const spinner = createSpinner("Fetching deployments...");
    spinner.start();
    try {
      const client = createClient(program2.opts().apiUrl);
      const data = await client.listDeployments();
      spinner.stop();
      let deployments = data.deployments || [];
      if (opts.status) {
        deployments = deployments.filter(
          (d) => d.status === opts.status
        );
      }
      if (json) {
        printJson(deployments);
        return;
      }
      if (deployments.length === 0) {
        printInfo("No deployments found.");
        printInfo("Deploy one with: polaris deploy");
        return;
      }
      printTable(
        ["ID", "Name", "Template", "Status", "Created"],
        deployments.map((d) => [
          d.id.slice(0, 8),
          d.name,
          d.template_id,
          colorStatus(d.status),
          new Date(d.created_at).toLocaleDateString()
        ])
      );
    } catch (err) {
      spinner.stop();
      printError(
        err instanceof PolarisApiError ? err.toUserMessage() : String(err)
      );
      process.exit(1);
    }
  });
  instances.command("get <id>").description("Show deployment details").action(async (id) => {
    const json = program2.opts().json;
    const spinner = createSpinner("Fetching deployment...");
    spinner.start();
    try {
      const client = createClient(program2.opts().apiUrl);
      const d = await client.getDeployment(id);
      spinner.stop();
      if (json) {
        printJson(d);
        return;
      }
      console.log(`
${import_chalk7.default.bold(d.name)}
`);
      printKeyValue({
        ID: d.id,
        Template: d.template_id,
        Status: colorStatus(d.status),
        Provider: d.provider,
        Host: d.host || "\u2014",
        Port: d.port ? String(d.port) : "\u2014",
        "Access URL": d.access_url || "\u2014",
        Created: new Date(d.created_at).toLocaleString(),
        Started: d.started_at ? new Date(d.started_at).toLocaleString() : "\u2014"
      });
      if (d.error_message) {
        console.log(
          `
${import_chalk7.default.red("Error:")} ${d.error_message}`
        );
      }
    } catch (err) {
      spinner.stop();
      printError(
        err instanceof PolarisApiError ? err.toUserMessage() : String(err)
      );
      process.exit(1);
    }
  });
  instances.command("terminate <id>").alias("rm").description("Terminate a deployment").option("-y, --yes", "Skip confirmation").action(async (id, opts) => {
    const json = program2.opts().json;
    if (!opts.yes) {
      const ok = await (0, import_prompts2.confirm)({
        message: `Terminate deployment ${id}?`,
        default: false
      });
      if (!ok) {
        printInfo("Cancelled.");
        return;
      }
    }
    const spinner = createSpinner("Terminating...");
    spinner.start();
    try {
      const client = createClient(program2.opts().apiUrl);
      const result = await client.deleteDeployment(id);
      spinner.stop();
      if (json) {
        printJson(result);
      } else {
        printSuccess(`Deployment ${id} terminated.`);
      }
    } catch (err) {
      spinner.stop();
      printError(
        err instanceof PolarisApiError ? err.toUserMessage() : String(err)
      );
      process.exit(1);
    }
  });
  program2.command("ssh <id>").description("SSH into a running deployment").action(async (id) => {
    const spinner = createSpinner("Fetching connection info...");
    spinner.start();
    try {
      const client = createClient(program2.opts().apiUrl);
      const d = await client.getDeployment(id);
      spinner.stop();
      if (d.status !== "running") {
        printError(
          `Deployment is ${d.status}. SSH is only available for running instances.`
        );
        process.exit(1);
      }
      if (!d.host || !d.port) {
        printError("No SSH connection info available for this deployment.");
        process.exit(1);
      }
      const sshHost = d.host;
      const sshPort = String(d.port);
      const sshUser = "root";
      printInfo(`Connecting to ${sshUser}@${sshHost}:${sshPort}...`);
      const child = (0, import_node_child_process.spawn)(
        "ssh",
        ["-o", "StrictHostKeyChecking=no", "-p", sshPort, `${sshUser}@${sshHost}`],
        { stdio: "inherit" }
      );
      child.on("exit", (code) => {
        process.exit(code || 0);
      });
    } catch (err) {
      spinner.stop();
      printError(
        err instanceof PolarisApiError ? err.toUserMessage() : String(err)
      );
      process.exit(1);
    }
  });
}

// src/commands/ssh-keys.ts
var fs2 = __toESM(require("fs"));
var path2 = __toESM(require("path"));
var os2 = __toESM(require("os"));
var import_chalk8 = __toESM(require("chalk"));
function registerSshKeysCommand(program2) {
  const sshKeys = program2.command("ssh-keys").description("Manage SSH public keys");
  sshKeys.command("list").alias("ls").description("List your SSH keys").action(async () => {
    const json = program2.opts().json;
    const spinner = createSpinner("Fetching SSH keys...");
    spinner.start();
    try {
      const client = createClient(program2.opts().apiUrl);
      const data = await client.listApiKeys();
      spinner.stop();
      if (json) {
        printJson(data);
        return;
      }
      printInfo(
        "SSH key management is available in the dashboard: https://polaris.computer/dashboard/settings"
      );
    } catch (err) {
      spinner.stop();
      printError(
        err instanceof PolarisApiError ? err.toUserMessage() : String(err)
      );
      process.exit(1);
    }
  });
  sshKeys.command("add").description("Add an SSH public key").option("--file <path>", "Path to public key file").option("--name <name>", "Key name").action(async (opts) => {
    const json = program2.opts().json;
    let keyContent;
    let keyName = opts.name;
    if (opts.file) {
      const filePath = opts.file.replace("~", os2.homedir());
      if (!fs2.existsSync(filePath)) {
        printError(`File not found: ${filePath}`);
        process.exit(1);
      }
      keyContent = fs2.readFileSync(filePath, "utf-8").trim();
    } else {
      const defaultPaths = [
        path2.join(os2.homedir(), ".ssh", "id_ed25519.pub"),
        path2.join(os2.homedir(), ".ssh", "id_rsa.pub")
      ];
      const found = defaultPaths.find((p) => fs2.existsSync(p));
      if (found) {
        printInfo(`Found SSH key: ${found}`);
        const ok = await (0, import_prompts2.confirm)({
          message: `Use ${path2.basename(found)}?`,
          default: true
        });
        if (ok) {
          keyContent = fs2.readFileSync(found, "utf-8").trim();
        } else {
          const filePath = await (0, import_prompts2.input)({
            message: "Path to public key file:"
          });
          keyContent = fs2.readFileSync(filePath.replace("~", os2.homedir()), "utf-8").trim();
        }
      } else {
        const filePath = await (0, import_prompts2.input)({
          message: "Path to public key file:",
          default: "~/.ssh/id_ed25519.pub"
        });
        keyContent = fs2.readFileSync(filePath.replace("~", os2.homedir()), "utf-8").trim();
      }
    }
    if (!keyContent.startsWith("ssh-")) {
      printError("Invalid SSH public key format. Key should start with ssh-ed25519, ssh-rsa, etc.");
      process.exit(1);
    }
    if (!keyName) {
      keyName = await (0, import_prompts2.input)({
        message: "Key name:",
        default: `cli-${Date.now().toString(36).slice(-4)}`
      });
    }
    if (json) {
      printJson({
        success: true,
        message: "SSH key upload \u2014 use the dashboard for full SSH key management",
        name: keyName,
        key_type: keyContent.split(" ")[0]
      });
    } else {
      printInfo(
        "SSH key management coming soon via API. For now, manage keys at:"
      );
      printInfo(
        import_chalk8.default.underline("https://polaris.computer/dashboard/settings")
      );
    }
  });
  sshKeys.command("remove <id>").description("Remove an SSH key").action(async () => {
    printInfo(
      "SSH key management is available in the dashboard: https://polaris.computer/dashboard/settings"
    );
  });
}

// src/commands/ai.ts
var import_chalk9 = __toESM(require("chalk"));

// src/lib/streaming.ts
async function consumeSSEStream(body, onToken, onDone) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let fullText = "";
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
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
          const content = parsed.choices?.[0]?.delta?.content || parsed.choices?.[0]?.text || parsed.content || parsed.token || "";
          if (content) {
            fullText += content;
            onToken(content);
          }
        } catch {
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

// src/commands/ai.ts
var readline = __toESM(require("readline"));
var AVAILABLE_MODELS = [
  { id: "llama3.2", name: "Llama 3.2 (3B)", provider: "ollama", context: "128K" },
  { id: "llama3.1", name: "Llama 3.1 (8B)", provider: "ollama", context: "128K" },
  { id: "llama3.1:70b", name: "Llama 3.1 (70B)", provider: "ollama", context: "128K" },
  { id: "mistral", name: "Mistral (7B)", provider: "ollama", context: "32K" },
  { id: "mixtral", name: "Mixtral 8x7B", provider: "ollama", context: "32K" },
  { id: "codellama", name: "Code Llama", provider: "ollama", context: "16K" },
  { id: "deepseek-coder", name: "DeepSeek Coder", provider: "ollama", context: "16K" },
  { id: "phi3", name: "Phi-3", provider: "ollama", context: "128K" },
  { id: "gemma2", name: "Gemma 2", provider: "ollama", context: "8K" },
  { id: "qwen2.5", name: "Qwen 2.5", provider: "ollama", context: "128K" }
];
function registerAiCommand(program2) {
  const ai = program2.command("ai").description("AI model inference");
  ai.command("models").description("List available AI models").action(async () => {
    const json = program2.opts().json;
    if (json) {
      printJson(AVAILABLE_MODELS);
      return;
    }
    printTable(
      ["Model ID", "Name", "Provider", "Context"],
      AVAILABLE_MODELS.map((m) => [m.id, m.name, m.provider, m.context])
    );
  });
  ai.command("chat [prompt]").description("Chat with an AI model (streaming)").option("--model <model>", "Model to use", "llama3.2").option("--system <prompt>", "System prompt").action(async (promptArg, opts) => {
    const json = program2.opts().json;
    if (promptArg) {
      await runOneShot(program2, promptArg, opts, json);
    } else {
      await runInteractive(program2, opts, json);
    }
  });
}
async function runOneShot(program2, prompt, opts, json) {
  const spinner = createSpinner("Thinking...");
  spinner.start();
  try {
    const client = createClient(program2.opts().apiUrl);
    const messages = [];
    if (opts.system) {
      messages.push({ role: "system", content: opts.system });
    }
    messages.push({ role: "user", content: prompt });
    const res = await client.rawFetch("POST", "/api/ai/chat", {
      model: opts.model,
      messages,
      stream: !json
    });
    spinner.stop();
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      printError(
        err.detail || `API error: ${res.status}`
      );
      process.exit(1);
    }
    if (json) {
      const data = await res.json();
      printJson(data);
      return;
    }
    if (res.body) {
      console.log();
      await consumeSSEStream(
        res.body,
        (token) => process.stdout.write(token),
        () => console.log("\n")
      );
    }
  } catch (err) {
    spinner.stop();
    printError(
      err instanceof PolarisApiError ? err.toUserMessage() : String(err)
    );
    process.exit(1);
  }
}
async function runInteractive(program2, opts, json) {
  console.log(
    import_chalk9.default.hex("#2D5A47").bold(`
  Polaris AI Chat`) + import_chalk9.default.dim(` (${opts.model})`)
  );
  console.log(import_chalk9.default.dim("  Type /quit to exit\n"));
  const messages = [];
  if (opts.system) {
    messages.push({ role: "system", content: opts.system });
  }
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });
  const askQuestion = () => new Promise((resolve) => {
    rl.question(import_chalk9.default.hex("#4A7C59")("you > "), (answer) => {
      resolve(answer);
    });
  });
  while (true) {
    const userInput = await askQuestion();
    if (!userInput.trim()) continue;
    if (userInput.trim() === "/quit" || userInput.trim() === "/exit") {
      console.log(import_chalk9.default.dim("\nGoodbye!"));
      rl.close();
      break;
    }
    messages.push({ role: "user", content: userInput });
    try {
      const client = createClient(program2.opts().apiUrl);
      const res = await client.rawFetch("POST", "/api/ai/chat", {
        model: opts.model,
        messages,
        stream: true
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        printError(
          err.detail || `API error: ${res.status}`
        );
        continue;
      }
      process.stdout.write(import_chalk9.default.hex("#2D5A47")("ai > "));
      let fullResponse = "";
      if (res.body) {
        fullResponse = await consumeSSEStream(
          res.body,
          (token) => process.stdout.write(token),
          () => console.log("\n")
        );
      }
      messages.push({ role: "assistant", content: fullResponse });
    } catch (err) {
      printError(
        err instanceof PolarisApiError ? err.toUserMessage() : String(err)
      );
    }
  }
}

// src/commands/db.ts
function registerDbCommand(program2) {
  const db = program2.command("db").description("Manage databases");
  db.command("list").alias("ls").description("List your databases").action(async () => {
    const json = program2.opts().json;
    const spinner = createSpinner("Fetching databases...");
    spinner.start();
    try {
      const client = createClient(program2.opts().apiUrl);
      const data = await client.getUserStorage();
      spinner.stop();
      if (json) {
        printJson(data);
        return;
      }
      printInfo(
        "Managed databases coming soon. Storage volumes are available now."
      );
      if (data.volumes && data.volumes.length > 0) {
        printTable(
          ["ID", "Bucket", "Size", "Created"],
          data.volumes.map((v) => [
            v.id?.slice(0, 8) || "\u2014",
            v.bucket_name,
            formatBytes(v.size_bytes || 0),
            v.created_at ? new Date(v.created_at).toLocaleDateString() : "\u2014"
          ])
        );
      }
    } catch (err) {
      spinner.stop();
      printError(
        err instanceof PolarisApiError ? err.toUserMessage() : String(err)
      );
      process.exit(1);
    }
  });
  db.command("create").description("Create a new database").option("--engine <engine>", "Database engine (pg, redis, mongodb)").option("--name <name>", "Database name").option("--region <region>", "Region", "lagos").action(async (opts) => {
    const json = program2.opts().json;
    const engine = opts.engine || await (0, import_prompts2.select)({
      message: "Database engine:",
      choices: [
        { name: "PostgreSQL", value: "pg" },
        { name: "Redis", value: "redis" },
        { name: "MongoDB", value: "mongodb" }
      ]
    });
    const name = opts.name || await (0, import_prompts2.input)({
      message: "Database name:",
      default: `${engine}-${Date.now().toString(36).slice(-4)}`
    });
    if (json) {
      printJson({
        message: "Managed databases coming soon",
        engine,
        name,
        region: opts.region
      });
    } else {
      printInfo("Managed databases are coming soon.");
      printInfo(
        "Track progress at: https://polaris.computer/dashboard"
      );
    }
  });
  db.command("delete <id>").description("Delete a database").option("-y, --yes", "Skip confirmation").action(async (id, opts) => {
    if (!opts.yes) {
      const ok = await (0, import_prompts2.confirm)({
        message: `Delete database ${id}? This cannot be undone.`,
        default: false
      });
      if (!ok) {
        printInfo("Cancelled.");
        return;
      }
    }
    printInfo("Managed database deletion coming soon.");
  });
  db.command("connect <id>").description("Get connection string for a database").action(async (id) => {
    printInfo("Managed databases coming soon.");
  });
}
function formatBytes(bytes) {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

// src/commands/storage.ts
function registerStorageCommand(program2) {
  const storage = program2.command("storage").description("Manage storage buckets");
  storage.command("list").alias("ls").description("List your storage volumes").action(async () => {
    const json = program2.opts().json;
    const spinner = createSpinner("Fetching storage...");
    spinner.start();
    try {
      const client = createClient(program2.opts().apiUrl);
      const data = await client.getUserStorage();
      spinner.stop();
      if (json) {
        printJson(data);
        return;
      }
      if (!data.volumes || data.volumes.length === 0) {
        printInfo("No storage volumes found.");
        printInfo("Create one with: polaris storage create");
        return;
      }
      printTable(
        ["Bucket", "Provider", "Size", "Created"],
        data.volumes.map((v) => [
          v.bucket_name,
          v.provider || "storj",
          formatBytes2(v.size_bytes || 0),
          v.created_at ? new Date(v.created_at).toLocaleDateString() : "\u2014"
        ])
      );
    } catch (err) {
      spinner.stop();
      printError(
        err instanceof PolarisApiError ? err.toUserMessage() : String(err)
      );
      process.exit(1);
    }
  });
  storage.command("create").description("Create a new storage bucket").option("--name <name>", "Bucket name").option("--region <region>", "Region", "lagos").option("--access <access>", "Access level (private, public-read)").action(async (opts) => {
    const json = program2.opts().json;
    const name = opts.name || await (0, import_prompts2.input)({
      message: "Bucket name:",
      validate: (v) => /^[a-z0-9][a-z0-9.-]+$/.test(v) || "Lowercase letters, numbers, dots, hyphens"
    });
    const access = opts.access || await (0, import_prompts2.select)({
      message: "Access level:",
      choices: [
        { name: "Private (default)", value: "private" },
        { name: "Public read", value: "public-read" }
      ]
    });
    if (json) {
      printJson({ message: "Storage creation via CLI coming soon", name, access });
    } else {
      printInfo("Storage bucket creation via CLI is coming soon.");
      printInfo(
        "Manage storage at: https://polaris.computer/dashboard"
      );
    }
  });
  storage.command("delete <name>").description("Delete a storage bucket").option("-y, --yes", "Skip confirmation").action(async (name, opts) => {
    if (!opts.yes) {
      const ok = await (0, import_prompts2.confirm)({
        message: `Delete bucket "${name}"? This cannot be undone.`,
        default: false
      });
      if (!ok) {
        printInfo("Cancelled.");
        return;
      }
    }
    printInfo("Storage deletion via CLI is coming soon.");
  });
}
function formatBytes2(bytes) {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

// src/commands/billing.ts
var import_chalk10 = __toESM(require("chalk"));
function registerBillingCommand(program2) {
  const billing = program2.command("billing").description("Billing and subscription info");
  billing.command("plans").description("List subscription plans").action(async () => {
    const json = program2.opts().json;
    const plans = [
      {
        name: "Free",
        price: "$0/mo",
        compute: "30 min",
        storage: "\u2014",
        api_keys: "3"
      },
      {
        name: "Basic",
        price: "$10/mo",
        compute: "300 min",
        storage: "10 GB",
        api_keys: "10"
      },
      {
        name: "Premium",
        price: "$20/mo",
        compute: "1000 min",
        storage: "100 GB",
        api_keys: "25"
      }
    ];
    if (json) {
      printJson(plans);
      return;
    }
    printTable(
      ["Plan", "Price", "Compute", "Storage", "API Keys"],
      plans.map((p) => [p.name, p.price, p.compute, p.storage, p.api_keys])
    );
    console.log(
      import_chalk10.default.dim("\n  Upgrade at: https://polaris.computer/pricing\n")
    );
  });
  billing.command("status").description("Show your current subscription").action(async () => {
    const json = program2.opts().json;
    const spinner = createSpinner("Fetching billing info...");
    spinner.start();
    try {
      const client = createClient(program2.opts().apiUrl);
      const stats = await client.getStats();
      spinner.stop();
      if (json) {
        printJson(stats);
        return;
      }
      console.log();
      printKeyValue({
        Plan: stats.tier.charAt(0).toUpperCase() + stats.tier.slice(1),
        "Compute Used": `${stats.compute_minutes_used} / ${stats.compute_minutes_limit} min`,
        "Storage Used": `${formatBytes3(stats.storage_bytes_used)} / ${formatBytes3(stats.storage_bytes_limit)}`,
        "Active Deployments": String(stats.active_deployments),
        "API Keys": String(stats.api_keys_count)
      });
      console.log();
    } catch (err) {
      spinner.stop();
      printError(
        err instanceof PolarisApiError ? err.toUserMessage() : String(err)
      );
      process.exit(1);
    }
  });
  billing.command("transactions").description("View payment history").action(async () => {
    const json = program2.opts().json;
    const spinner = createSpinner("Fetching transactions...");
    spinner.start();
    try {
      const client = createClient(program2.opts().apiUrl);
      const usage = await client.getUsage();
      spinner.stop();
      if (json) {
        printJson(usage);
        return;
      }
      console.log();
      printKeyValue({
        "Total Requests": String(usage.total_requests),
        "This Month": String(usage.this_month),
        "Last Month": String(usage.last_month)
      });
      if (usage.key_usage && usage.key_usage.length > 0) {
        console.log(import_chalk10.default.dim("\n  Usage by API key:\n"));
        printTable(
          ["Key", "Requests", "Last Used"],
          usage.key_usage.map((k) => [
            k.name,
            String(k.total_requests),
            k.last_used ? new Date(k.last_used).toLocaleDateString() : "Never"
          ])
        );
      }
    } catch (err) {
      spinner.stop();
      printError(
        err instanceof PolarisApiError ? err.toUserMessage() : String(err)
      );
      process.exit(1);
    }
  });
}
function formatBytes3(bytes) {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

// src/index.ts
var program = new import_commander.Command();
program.name("polaris").description("Polaris Cloud CLI \u2014 GPU compute at your fingertips").version("0.1.0", "-v, --version").option("-j, --json", "Output raw JSON (for scripting)").option("--no-color", "Disable colored output").option("--api-url <url>", "Override API endpoint").hook("preAction", () => {
  if (program.opts().noColor) {
    process.env.NO_COLOR = "1";
  }
});
registerAuthCommand(program);
registerHealthCommand(program);
registerConfigCommand(program);
registerComputeCommand(program);
registerDeployCommand(program);
registerInstancesCommand(program);
registerSshKeysCommand(program);
registerAiCommand(program);
registerDbCommand(program);
registerStorageCommand(program);
registerBillingCommand(program);
program.action(() => {
  printBanner();
  program.outputHelp();
});
program.parseAsync(process.argv).catch((err) => {
  console.error(err);
  process.exit(1);
});
//# sourceMappingURL=index.js.map