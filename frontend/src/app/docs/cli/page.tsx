"use client";

import Link from "next/link";
import { useState } from "react";
import { SignedIn, SignedOut } from "@clerk/nextjs";
import { AT_CAPACITY } from "@/lib/config";

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className="absolute top-3 right-3 rounded-md bg-white/10 px-2 py-1 text-xs text-white/60 hover:text-white hover:bg-white/20 transition-colors"
    >
      {copied ? "Copied!" : "Copy"}
    </button>
  );
}

function CodeBlock({ code, language }: { code: string; language?: string }) {
  return (
    <div className="relative group rounded-lg bg-forest-dark overflow-hidden my-4">
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/10">
        <span className="text-xs text-white/40 font-mono">{language || "bash"}</span>
        <CopyButton text={code} />
      </div>
      <pre className="p-4 overflow-x-auto">
        <code className="text-sm font-mono text-white/80 leading-relaxed">{code}</code>
      </pre>
    </div>
  );
}

const commands = [
  {
    name: "auth login",
    description: "Authenticate with your Polaris account via browser-based OAuth.",
    usage: "polaris auth login",
    options: [],
    examples: [
      { desc: "Log in to your account", code: "polaris auth login" },
    ],
  },
  {
    name: "auth logout",
    description: "Log out and clear stored credentials.",
    usage: "polaris auth logout",
    options: [],
    examples: [
      { desc: "Log out", code: "polaris auth logout" },
    ],
  },
  {
    name: "auth status",
    description: "Check your current authentication status and display the logged-in user.",
    usage: "polaris auth status",
    options: [],
    examples: [
      { desc: "Check if you're logged in", code: "polaris auth status" },
    ],
  },
  {
    name: "deploy",
    description: "Deploy a new instance from a template. This creates a GPU-powered virtual machine with the selected template pre-configured.",
    usage: "polaris deploy [options]",
    options: [
      { flag: "--template <name>", desc: "Template to deploy (e.g., ollama, jupyter, terminal)" },
      { flag: "--name <name>", desc: "Name for the deployment" },
      { flag: "--region <region>", desc: "Deployment region (default: lagos)" },
      { flag: "--gpu <type>", desc: "GPU type to use (default: auto)" },
    ],
    examples: [
      { desc: "Deploy Ollama with a custom name", code: "polaris deploy --template ollama --name my-llm" },
      { desc: "Deploy Jupyter in a specific region", code: "polaris deploy --template jupyter --name analysis --region lagos" },
      { desc: "Deploy with a specific GPU", code: "polaris deploy --template terminal --name dev --gpu a100" },
    ],
  },
  {
    name: "instances list",
    description: "List all your deployments with their current status, template, and connection details.",
    usage: "polaris instances list [options]",
    options: [
      { flag: "--status <status>", desc: "Filter by status (running, stopped, pending)" },
      { flag: "--json", desc: "Output in JSON format" },
    ],
    examples: [
      { desc: "List all instances", code: "polaris instances list" },
      { desc: "List only running instances", code: "polaris instances list --status running" },
      { desc: "Output as JSON for scripting", code: "polaris instances list --json" },
    ],
  },
  {
    name: "instances stop",
    description: "Stop a running instance. The instance can be restarted later.",
    usage: "polaris instances stop <id>",
    options: [],
    examples: [
      { desc: "Stop an instance by ID", code: "polaris instances stop a7f3b291" },
    ],
  },
  {
    name: "instances delete",
    description: "Permanently delete an instance and all associated data. This action cannot be undone.",
    usage: "polaris instances delete <id>",
    options: [
      { flag: "--force", desc: "Skip confirmation prompt" },
    ],
    examples: [
      { desc: "Delete an instance", code: "polaris instances delete a7f3b291" },
      { desc: "Force delete without confirmation", code: "polaris instances delete a7f3b291 --force" },
    ],
  },
  {
    name: "templates list",
    description: "List all available deployment templates with descriptions and resource requirements.",
    usage: "polaris templates list",
    options: [
      { flag: "--json", desc: "Output in JSON format" },
    ],
    examples: [
      { desc: "List all templates", code: "polaris templates list" },
    ],
  },
  {
    name: "keys generate",
    description: "Generate a new API key. The key is displayed once and cannot be retrieved again.",
    usage: "polaris keys generate [options]",
    options: [
      { flag: "--name <name>", desc: "A descriptive name for the key" },
    ],
    examples: [
      { desc: "Generate a named API key", code: "polaris keys generate --name production-api" },
      { desc: "Generate a key for CI/CD", code: "polaris keys generate --name github-actions" },
    ],
  },
  {
    name: "keys list",
    description: "List all your API keys with their names, creation dates, and last used timestamps.",
    usage: "polaris keys list",
    options: [],
    examples: [
      { desc: "List all API keys", code: "polaris keys list" },
    ],
  },
  {
    name: "keys revoke",
    description: "Revoke an API key immediately. Any applications using this key will lose access.",
    usage: "polaris keys revoke <id>",
    options: [],
    examples: [
      { desc: "Revoke an API key", code: "polaris keys revoke key_abc123" },
    ],
  },
  {
    name: "usage",
    description: "View your current usage statistics, billing information, and resource consumption.",
    usage: "polaris usage",
    options: [
      { flag: "--period <period>", desc: "Time period: day, week, month (default: month)" },
      { flag: "--json", desc: "Output in JSON format" },
    ],
    examples: [
      { desc: "View this month's usage", code: "polaris usage" },
      { desc: "View weekly usage", code: "polaris usage --period week" },
    ],
  },
];

const sidebarItems = [
  { label: "Installation", slug: "installation" },
  { label: "Authentication", slug: "authentication" },
  ...commands.map((cmd) => ({
    label: cmd.name,
    slug: cmd.name.replace(/\s+/g, "-"),
  })),
  { label: "Configuration", slug: "configuration" },
  { label: "Environment Variables", slug: "env-vars" },
];

export default function CLIReferencePage() {
  const [activeSection, setActiveSection] = useState("installation");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const scrollToSection = (slug: string) => {
    setActiveSection(slug);
    const el = document.getElementById(slug);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    setMobileMenuOpen(false);
  };

  return (
    <div className="flex min-h-screen flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-8 py-4 border-b border-mist">
        <Link href="/" className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-forest flex items-center justify-center">
            <span className="text-white font-bold text-sm">P</span>
          </div>
          <span className="text-lg font-semibold text-forest-dark">
            Polaris Computer
          </span>
        </Link>
        <nav className="flex items-center gap-4">
          <Link
            href="/docs"
            className="text-sm font-medium text-forest transition-colors"
          >
            Docs
          </Link>
          <Link
            href="/pricing"
            className="text-sm font-medium text-forest-dark hover:text-forest transition-colors"
          >
            Pricing
          </Link>
          {AT_CAPACITY ? (
            <SignedOut>
              <a
                href="/#waitlist"
                className="rounded-lg bg-forest px-4 py-2 text-sm font-medium text-white hover:bg-forest-hover transition-colors"
              >
                Join Waitlist
              </a>
            </SignedOut>
          ) : (
            <SignedOut>
              <Link
                href="/sign-in"
                className="text-sm font-medium text-forest-dark hover:text-forest transition-colors"
              >
                Sign in
              </Link>
              <Link
                href="/sign-up"
                className="rounded-lg bg-forest px-4 py-2 text-sm font-medium text-white hover:bg-forest-hover transition-colors"
              >
                Get started
              </Link>
            </SignedOut>
          )}
          <SignedIn>
            <Link
              href="/dashboard"
              className="rounded-lg bg-forest px-4 py-2 text-sm font-medium text-white hover:bg-forest-hover transition-colors"
            >
              Dashboard
            </Link>
          </SignedIn>
        </nav>
      </header>

      <div className="flex flex-1">
        {/* Mobile menu toggle */}
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="lg:hidden fixed bottom-6 right-6 z-50 rounded-full bg-forest p-3 text-white shadow-lg hover:bg-forest-hover transition-colors"
        >
          <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            {mobileMenuOpen ? (
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
            )}
          </svg>
        </button>

        {/* Sidebar */}
        <aside
          className={`${
            mobileMenuOpen ? "translate-x-0" : "-translate-x-full"
          } lg:translate-x-0 fixed lg:sticky top-0 lg:top-[65px] left-0 z-40 h-screen lg:h-[calc(100vh-65px)] w-64 border-r border-mist bg-white overflow-y-auto transition-transform duration-200`}
        >
          <nav className="p-6">
            <div className="mb-4">
              <Link href="/docs" className="text-xs text-forest-dark/50 hover:text-forest transition-colors">
                &larr; Back to Docs
              </Link>
            </div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-forest-dark/50 mb-3">
              CLI Reference
            </h3>
            <ul className="space-y-1">
              {sidebarItems.map((item) => (
                <li key={item.slug}>
                  <button
                    onClick={() => scrollToSection(item.slug)}
                    className={`block w-full text-left rounded-md px-3 py-1.5 text-sm transition-colors ${
                      activeSection === item.slug
                        ? "bg-forest/10 text-forest font-medium"
                        : "text-forest-dark/70 hover:text-forest-dark hover:bg-sage"
                    }`}
                  >
                    {item.label}
                  </button>
                </li>
              ))}
            </ul>
          </nav>
        </aside>

        {/* Backdrop for mobile */}
        {mobileMenuOpen && (
          <div
            className="fixed inset-0 z-30 bg-black/20 lg:hidden"
            onClick={() => setMobileMenuOpen(false)}
          />
        )}

        {/* Main content */}
        <main className="flex-1 px-8 py-12 lg:px-16 max-w-4xl">
          <h1 className="text-4xl font-bold tracking-tight text-forest-dark">
            CLI Reference
          </h1>
          <p className="mt-4 text-lg text-forest-dark/70 leading-relaxed">
            Complete reference for the Polaris command-line interface. Deploy, manage, and monitor your GPU instances from the terminal.
          </p>

          {/* Installation */}
          <section id="installation" className="mt-16">
            <h2 className="text-2xl font-semibold text-forest-dark border-b border-mist pb-3">
              Installation
            </h2>

            <div className="mt-6 space-y-6">
              <div>
                <h3 className="text-lg font-medium text-forest-dark">npm (recommended)</h3>
                <CodeBlock code="npm install -g @polaris-cloud/cli" />
              </div>

              <div>
                <h3 className="text-lg font-medium text-forest-dark">yarn</h3>
                <CodeBlock code="yarn global add @polaris-cloud/cli" />
              </div>

              <div>
                <h3 className="text-lg font-medium text-forest-dark">npx (no install)</h3>
                <p className="mt-2 text-sm text-forest-dark/70">
                  Run any command without installing globally:
                </p>
                <CodeBlock code="npx @polaris-cloud/cli deploy --template ollama" />
              </div>

              <div>
                <h3 className="text-lg font-medium text-forest-dark">Verify installation</h3>
                <CodeBlock code={`polaris --version\n# polaris/1.0.0 linux-x64 node-v20.0.0`} />
              </div>
            </div>
          </section>

          {/* Authentication */}
          <section id="authentication" className="mt-16">
            <h2 className="text-2xl font-semibold text-forest-dark border-b border-mist pb-3">
              Authentication
            </h2>
            <p className="mt-4 text-forest-dark/70">
              The CLI supports two authentication methods: browser-based OAuth login and API key authentication.
            </p>

            <div className="mt-6 space-y-6">
              <div>
                <h3 className="text-lg font-medium text-forest-dark">Browser login</h3>
                <p className="mt-2 text-sm text-forest-dark/70">
                  Opens your default browser for secure authentication.
                </p>
                <CodeBlock code="polaris auth login" />
              </div>

              <div>
                <h3 className="text-lg font-medium text-forest-dark">API key</h3>
                <p className="mt-2 text-sm text-forest-dark/70">
                  Set the <code className="rounded bg-forest-dark/10 px-1.5 py-0.5 text-xs font-mono text-forest-dark">POLARIS_API_KEY</code> environment variable for headless environments.
                </p>
                <CodeBlock code="export POLARIS_API_KEY=pi_sk_your_key_here" />
              </div>
            </div>
          </section>

          {/* Commands */}
          <section className="mt-16">
            <h2 className="text-2xl font-semibold text-forest-dark border-b border-mist pb-3">
              Commands
            </h2>

            {/* Command overview table */}
            <div className="mt-6 overflow-hidden rounded-xl border border-mist">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-mist bg-stone">
                    <th className="px-4 py-3 text-left text-sm font-semibold text-forest-dark">Command</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-forest-dark">Description</th>
                  </tr>
                </thead>
                <tbody className="text-sm">
                  {commands.map((cmd) => (
                    <tr key={cmd.name} className="border-b border-mist last:border-b-0">
                      <td className="px-4 py-3">
                        <button
                          onClick={() => scrollToSection(cmd.name.replace(/\s+/g, "-"))}
                          className="font-mono text-xs text-forest hover:underline"
                        >
                          polaris {cmd.name}
                        </button>
                      </td>
                      <td className="px-4 py-3 text-forest-dark/70">{cmd.description.split(".")[0]}.</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Individual command sections */}
            {commands.map((cmd) => (
              <div
                key={cmd.name}
                id={cmd.name.replace(/\s+/g, "-")}
                className="mt-12 scroll-mt-8"
              >
                <h3 className="text-xl font-semibold text-forest-dark flex items-center gap-3">
                  <code className="rounded-lg bg-forest-dark/10 px-3 py-1 text-base font-mono">
                    polaris {cmd.name}
                  </code>
                </h3>
                <p className="mt-3 text-forest-dark/70">{cmd.description}</p>

                <div className="mt-4">
                  <h4 className="text-sm font-semibold text-forest-dark/80 uppercase tracking-wider">Usage</h4>
                  <CodeBlock code={cmd.usage} />
                </div>

                {cmd.options.length > 0 && (
                  <div className="mt-4">
                    <h4 className="text-sm font-semibold text-forest-dark/80 uppercase tracking-wider mb-3">Options</h4>
                    <div className="overflow-hidden rounded-lg border border-mist">
                      <table className="w-full">
                        <tbody className="text-sm">
                          {cmd.options.map((opt) => (
                            <tr key={opt.flag} className="border-b border-mist last:border-b-0">
                              <td className="px-4 py-2 font-mono text-xs text-forest whitespace-nowrap">{opt.flag}</td>
                              <td className="px-4 py-2 text-forest-dark/70">{opt.desc}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {cmd.examples.length > 0 && (
                  <div className="mt-4">
                    <h4 className="text-sm font-semibold text-forest-dark/80 uppercase tracking-wider mb-3">Examples</h4>
                    {cmd.examples.map((ex) => (
                      <div key={ex.code} className="mb-3">
                        <p className="text-sm text-forest-dark/60 mb-1">{ex.desc}</p>
                        <CodeBlock code={ex.code} />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </section>

          {/* Configuration */}
          <section id="configuration" className="mt-16">
            <h2 className="text-2xl font-semibold text-forest-dark border-b border-mist pb-3">
              Configuration
            </h2>
            <p className="mt-4 text-forest-dark/70">
              The CLI stores its configuration at <code className="rounded bg-forest-dark/10 px-1.5 py-0.5 text-sm font-mono text-forest-dark">~/.polaris/config.json</code>.
            </p>
            <CodeBlock
              code={`{
  "apiUrl": "https://api.polaris.computer",
  "defaultRegion": "lagos",
  "defaultTemplate": "ollama",
  "token": "..."
}`}
              language="json"
            />
            <p className="mt-4 text-sm text-forest-dark/60">
              The token field is managed automatically by <code className="rounded bg-forest-dark/10 px-1 py-0.5 text-xs font-mono text-forest-dark">polaris auth login</code>. Do not edit it manually.
            </p>
          </section>

          {/* Environment Variables */}
          <section id="env-vars" className="mt-16 mb-16">
            <h2 className="text-2xl font-semibold text-forest-dark border-b border-mist pb-3">
              Environment Variables
            </h2>
            <p className="mt-4 text-forest-dark/70">
              Environment variables override configuration file values.
            </p>
            <div className="mt-6 overflow-hidden rounded-xl border border-mist">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-mist bg-stone">
                    <th className="px-4 py-3 text-left text-sm font-semibold text-forest-dark">Variable</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-forest-dark">Description</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-forest-dark">Default</th>
                  </tr>
                </thead>
                <tbody className="text-sm">
                  {[
                    ["POLARIS_API_KEY", "API key for authentication", "None"],
                    ["POLARIS_API_URL", "Override the API base URL", "https://api.polaris.computer"],
                    ["POLARIS_REGION", "Default deployment region", "lagos"],
                    ["POLARIS_CONFIG_DIR", "Custom config directory", "~/.polaris"],
                    ["NO_COLOR", "Disable colored output", "Unset"],
                  ].map(([variable, desc, def]) => (
                    <tr key={variable} className="border-b border-mist last:border-b-0">
                      <td className="px-4 py-3 font-mono text-xs text-forest whitespace-nowrap">{variable}</td>
                      <td className="px-4 py-3 text-forest-dark/70">{desc}</td>
                      <td className="px-4 py-3 text-forest-dark/50 text-xs">{def}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </main>
      </div>

      {/* Footer */}
      <footer className="border-t border-mist px-8 py-6 text-center text-sm text-forest-dark/50">
        Polaris Computer
      </footer>
    </div>
  );
}
