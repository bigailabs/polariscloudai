"use client";

import Link from "next/link";
import { useState } from "react";
import { SignedIn, SignedOut } from "@clerk/nextjs";
import { AT_CAPACITY } from "@/lib/config";

const sidebarSections = [
  {
    title: "Getting Started",
    items: [
      { label: "Quick Start", slug: "quick-start" },
      { label: "Installation", slug: "installation" },
      { label: "Authentication", slug: "authentication" },
    ],
  },
  {
    title: "CLI Reference",
    items: [
      { label: "Installation", slug: "cli-installation" },
      { label: "Commands", slug: "cli-commands" },
      { label: "Configuration", slug: "cli-configuration" },
    ],
    link: "/docs/cli",
  },
  {
    title: "API Reference",
    items: [
      { label: "Authentication", slug: "api-authentication" },
      { label: "Templates", slug: "api-templates" },
      { label: "Deployments", slug: "api-deployments" },
      { label: "API Keys", slug: "api-keys" },
      { label: "Usage & Billing", slug: "api-usage" },
    ],
    link: "/docs/api",
  },
  {
    title: "Templates",
    items: [
      { label: "Ollama Chat", slug: "template-ollama" },
      { label: "Jupyter Notebook", slug: "template-jupyter" },
      { label: "Development Terminal", slug: "template-terminal" },
      { label: "Cloud Computer", slug: "template-cloud" },
      { label: "Game Servers", slug: "template-games" },
    ],
  },
  {
    title: "Guides",
    items: [
      { label: "Deploy Your First Model", slug: "guide-deploy" },
      { label: "SSH Access", slug: "guide-ssh" },
      { label: "API Key Management", slug: "guide-api-keys" },
    ],
  },
];

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

export default function DocsPage() {
  const [activeSection, setActiveSection] = useState("quick-start");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

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
          } lg:translate-x-0 fixed lg:sticky top-0 lg:top-[65px] left-0 z-40 h-screen lg:h-[calc(100vh-65px)] w-72 border-r border-mist bg-white overflow-y-auto transition-transform duration-200`}
        >
          <nav className="p-6 space-y-6">
            {sidebarSections.map((section) => (
              <div key={section.title}>
                {section.link ? (
                  <Link
                    href={section.link}
                    className="text-xs font-semibold uppercase tracking-wider text-forest-dark/50 hover:text-forest transition-colors"
                  >
                    {section.title}
                  </Link>
                ) : (
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-forest-dark/50">
                    {section.title}
                  </h4>
                )}
                <ul className="mt-2 space-y-1">
                  {section.items.map((item) => (
                    <li key={item.slug}>
                      <button
                        onClick={() => {
                          setActiveSection(item.slug);
                          setMobileMenuOpen(false);
                        }}
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
              </div>
            ))}
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
          {/* Quick Start */}
          {activeSection === "quick-start" && (
            <div>
              <h1 className="text-4xl font-bold tracking-tight text-forest-dark">
                Quick Start
              </h1>
              <p className="mt-4 text-lg text-forest-dark/70 leading-relaxed">
                Get up and running with Polaris Computer in under 5 minutes.
              </p>

              <div className="mt-12 space-y-10">
                <div>
                  <div className="flex items-center gap-3">
                    <span className="flex h-8 w-8 items-center justify-center rounded-full bg-forest text-sm font-bold text-white">
                      1
                    </span>
                    <h2 className="text-xl font-semibold text-forest-dark">Install the CLI</h2>
                  </div>
                  <p className="mt-3 text-forest-dark/70 ml-11">
                    Install the Polaris CLI globally using npm.
                  </p>
                  <div className="ml-11">
                    <CodeBlock code="npm install -g @polaris-cloud/cli" />
                  </div>
                </div>

                <div>
                  <div className="flex items-center gap-3">
                    <span className="flex h-8 w-8 items-center justify-center rounded-full bg-forest text-sm font-bold text-white">
                      2
                    </span>
                    <h2 className="text-xl font-semibold text-forest-dark">Authenticate</h2>
                  </div>
                  <p className="mt-3 text-forest-dark/70 ml-11">
                    Log in with your Polaris account. This opens a browser window for authentication.
                  </p>
                  <div className="ml-11">
                    <CodeBlock code="polaris auth login" />
                  </div>
                </div>

                <div>
                  <div className="flex items-center gap-3">
                    <span className="flex h-8 w-8 items-center justify-center rounded-full bg-forest text-sm font-bold text-white">
                      3
                    </span>
                    <h2 className="text-xl font-semibold text-forest-dark">Deploy</h2>
                  </div>
                  <p className="mt-3 text-forest-dark/70 ml-11">
                    Deploy your first AI model using a pre-built template.
                  </p>
                  <div className="ml-11">
                    <CodeBlock code="polaris deploy --template ollama --name my-first-llm" />
                  </div>
                </div>

                <div>
                  <div className="flex items-center gap-3">
                    <span className="flex h-8 w-8 items-center justify-center rounded-full bg-forest text-sm font-bold text-white">
                      4
                    </span>
                    <h2 className="text-xl font-semibold text-forest-dark">Check Status</h2>
                  </div>
                  <p className="mt-3 text-forest-dark/70 ml-11">
                    View all your running instances and their status.
                  </p>
                  <div className="ml-11">
                    <CodeBlock code="polaris instances list" />
                  </div>
                </div>
              </div>

              <div className="mt-12 rounded-xl border border-mist bg-sage p-6">
                <h3 className="text-sm font-semibold text-forest-dark">What&apos;s next?</h3>
                <ul className="mt-3 space-y-2">
                  <li>
                    <button
                      onClick={() => setActiveSection("cli-commands")}
                      className="text-sm text-forest hover:underline"
                    >
                      Explore all CLI commands
                    </button>
                  </li>
                  <li>
                    <Link href="/docs/api" className="text-sm text-forest hover:underline">
                      Browse the API reference
                    </Link>
                  </li>
                  <li>
                    <button
                      onClick={() => setActiveSection("template-ollama")}
                      className="text-sm text-forest hover:underline"
                    >
                      Learn about templates
                    </button>
                  </li>
                </ul>
              </div>
            </div>
          )}

          {/* Installation */}
          {activeSection === "installation" && (
            <div>
              <h1 className="text-4xl font-bold tracking-tight text-forest-dark">
                Installation
              </h1>
              <p className="mt-4 text-lg text-forest-dark/70 leading-relaxed">
                Install the Polaris CLI and set up your development environment.
              </p>

              <div className="mt-10 space-y-8">
                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">Prerequisites</h2>
                  <ul className="mt-4 space-y-2 text-forest-dark/70">
                    <li className="flex items-start gap-2">
                      <svg className="mt-1 h-4 w-4 flex-shrink-0 text-forest" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                      </svg>
                      Node.js 18 or later
                    </li>
                    <li className="flex items-start gap-2">
                      <svg className="mt-1 h-4 w-4 flex-shrink-0 text-forest" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                      </svg>
                      A Polaris Computer account
                    </li>
                    <li className="flex items-start gap-2">
                      <svg className="mt-1 h-4 w-4 flex-shrink-0 text-forest" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                      </svg>
                      npm, yarn, or pnpm package manager
                    </li>
                  </ul>
                </div>

                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">Install via npm</h2>
                  <CodeBlock code="npm install -g @polaris-cloud/cli" />
                </div>

                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">Install via yarn</h2>
                  <CodeBlock code="yarn global add @polaris-cloud/cli" />
                </div>

                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">Run without installing</h2>
                  <p className="mt-2 text-forest-dark/70">
                    You can use npx to run the CLI without a global installation.
                  </p>
                  <CodeBlock code="npx @polaris-cloud/cli deploy --template ollama" />
                </div>

                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">Verify installation</h2>
                  <CodeBlock code="polaris --version" />
                </div>
              </div>
            </div>
          )}

          {/* Authentication */}
          {activeSection === "authentication" && (
            <div>
              <h1 className="text-4xl font-bold tracking-tight text-forest-dark">
                Authentication
              </h1>
              <p className="mt-4 text-lg text-forest-dark/70 leading-relaxed">
                Authenticate with Polaris to deploy and manage your instances.
              </p>

              <div className="mt-10 space-y-8">
                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">Browser login</h2>
                  <p className="mt-3 text-forest-dark/70">
                    The simplest way to authenticate. This opens your default browser where you can sign in with your Polaris account.
                  </p>
                  <CodeBlock code="polaris auth login" />
                </div>

                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">API key authentication</h2>
                  <p className="mt-3 text-forest-dark/70">
                    For CI/CD pipelines and automated environments, use an API key instead.
                  </p>
                  <CodeBlock code="export POLARIS_API_KEY=pi_sk_your_key_here" />
                  <p className="mt-3 text-forest-dark/70">
                    Generate API keys from your{" "}
                    <Link href="/dashboard" className="text-forest hover:underline">
                      dashboard
                    </Link>{" "}
                    or via the CLI:
                  </p>
                  <CodeBlock code="polaris keys generate --name ci-deploy" />
                </div>

                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">Check auth status</h2>
                  <CodeBlock code="polaris auth status" />
                </div>

                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">Log out</h2>
                  <CodeBlock code="polaris auth logout" />
                </div>
              </div>
            </div>
          )}

          {/* CLI Installation */}
          {activeSection === "cli-installation" && (
            <div>
              <h1 className="text-4xl font-bold tracking-tight text-forest-dark">
                CLI Installation
              </h1>
              <p className="mt-4 text-lg text-forest-dark/70 leading-relaxed">
                Install and configure the Polaris CLI for your platform.
              </p>
              <div className="mt-6 rounded-xl border border-forest/20 bg-forest/5 p-4">
                <p className="text-sm text-forest-dark/70">
                  For detailed installation instructions, see the{" "}
                  <Link href="/docs/cli" className="text-forest font-medium hover:underline">
                    full CLI Reference
                  </Link>.
                </p>
              </div>
              <div className="mt-8 space-y-6">
                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">Global install</h2>
                  <CodeBlock code="npm install -g @polaris-cloud/cli" />
                </div>
                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">One-off usage</h2>
                  <CodeBlock code="npx @polaris-cloud/cli --help" />
                </div>
              </div>
            </div>
          )}

          {/* CLI Commands */}
          {activeSection === "cli-commands" && (
            <div>
              <h1 className="text-4xl font-bold tracking-tight text-forest-dark">
                CLI Commands
              </h1>
              <p className="mt-4 text-lg text-forest-dark/70 leading-relaxed">
                Complete reference for all Polaris CLI commands.
              </p>
              <div className="mt-6 rounded-xl border border-forest/20 bg-forest/5 p-4">
                <p className="text-sm text-forest-dark/70">
                  See the{" "}
                  <Link href="/docs/cli" className="text-forest font-medium hover:underline">
                    full CLI Reference page
                  </Link>{" "}
                  for detailed usage, options, and examples for every command.
                </p>
              </div>

              <div className="mt-8">
                <div className="overflow-hidden rounded-xl border border-mist">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-mist bg-stone">
                        <th className="px-4 py-3 text-left text-sm font-semibold text-forest-dark">Command</th>
                        <th className="px-4 py-3 text-left text-sm font-semibold text-forest-dark">Description</th>
                      </tr>
                    </thead>
                    <tbody className="text-sm">
                      {[
                        ["polaris auth login", "Authenticate with Polaris"],
                        ["polaris auth logout", "Log out of your session"],
                        ["polaris auth status", "Check authentication status"],
                        ["polaris deploy", "Deploy a new instance from a template"],
                        ["polaris instances list", "List all your running instances"],
                        ["polaris instances stop <id>", "Stop a running instance"],
                        ["polaris instances delete <id>", "Delete an instance permanently"],
                        ["polaris templates list", "List available deployment templates"],
                        ["polaris keys generate", "Generate a new API key"],
                        ["polaris keys list", "List your API keys"],
                        ["polaris keys revoke <id>", "Revoke an API key"],
                        ["polaris usage", "View your current usage and billing"],
                      ].map(([cmd, desc]) => (
                        <tr key={cmd} className="border-b border-mist last:border-b-0">
                          <td className="px-4 py-3 font-mono text-xs text-forest">{cmd}</td>
                          <td className="px-4 py-3 text-forest-dark/70">{desc}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* CLI Configuration */}
          {activeSection === "cli-configuration" && (
            <div>
              <h1 className="text-4xl font-bold tracking-tight text-forest-dark">
                CLI Configuration
              </h1>
              <p className="mt-4 text-lg text-forest-dark/70 leading-relaxed">
                Configure the Polaris CLI for your workflow.
              </p>

              <div className="mt-10 space-y-8">
                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">Configuration file</h2>
                  <p className="mt-3 text-forest-dark/70">
                    The CLI stores configuration at <code className="rounded bg-forest-dark/10 px-1.5 py-0.5 text-sm font-mono text-forest-dark">~/.polaris/config.json</code>.
                  </p>
                  <CodeBlock
                    code={`{
  "apiUrl": "https://api.polaris.computer",
  "defaultRegion": "lagos",
  "defaultTemplate": "ollama"
}`}
                    language="json"
                  />
                </div>

                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">Environment variables</h2>
                  <div className="mt-4 overflow-hidden rounded-xl border border-mist">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-mist bg-stone">
                          <th className="px-4 py-3 text-left text-sm font-semibold text-forest-dark">Variable</th>
                          <th className="px-4 py-3 text-left text-sm font-semibold text-forest-dark">Description</th>
                        </tr>
                      </thead>
                      <tbody className="text-sm">
                        {[
                          ["POLARIS_API_KEY", "API key for authentication"],
                          ["POLARIS_API_URL", "Override the API base URL"],
                          ["POLARIS_REGION", "Default deployment region"],
                        ].map(([variable, desc]) => (
                          <tr key={variable} className="border-b border-mist last:border-b-0">
                            <td className="px-4 py-3 font-mono text-xs text-forest">{variable}</td>
                            <td className="px-4 py-3 text-forest-dark/70">{desc}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* API Authentication */}
          {activeSection === "api-authentication" && (
            <div>
              <h1 className="text-4xl font-bold tracking-tight text-forest-dark">
                API Authentication
              </h1>
              <p className="mt-4 text-lg text-forest-dark/70 leading-relaxed">
                Authenticate your API requests using bearer tokens.
              </p>
              <div className="mt-6 rounded-xl border border-forest/20 bg-forest/5 p-4">
                <p className="text-sm text-forest-dark/70">
                  See the{" "}
                  <Link href="/docs/api" className="text-forest font-medium hover:underline">
                    full API Reference
                  </Link>{" "}
                  for all endpoints and examples.
                </p>
              </div>
              <div className="mt-8">
                <h2 className="text-2xl font-semibold text-forest-dark">Bearer token</h2>
                <p className="mt-3 text-forest-dark/70">
                  Include your API key in the <code className="rounded bg-forest-dark/10 px-1.5 py-0.5 text-sm font-mono text-forest-dark">Authorization</code> header of every request.
                </p>
                <CodeBlock
                  code={`curl https://api.polaris.computer/api/auth/me \\
  -H "Authorization: Bearer pi_sk_your_key_here"`}
                />
              </div>
            </div>
          )}

          {/* API Templates */}
          {activeSection === "api-templates" && (
            <div>
              <h1 className="text-4xl font-bold tracking-tight text-forest-dark">Templates API</h1>
              <p className="mt-4 text-lg text-forest-dark/70">Browse and retrieve deployment templates.</p>
              <div className="mt-6 rounded-xl border border-forest/20 bg-forest/5 p-4">
                <p className="text-sm text-forest-dark/70">
                  <Link href="/docs/api" className="text-forest font-medium hover:underline">
                    View full API Reference
                  </Link>
                </p>
              </div>
              <div className="mt-8">
                <CodeBlock
                  code={`GET /api/templates
Authorization: Bearer pi_sk_...`}
                  language="http"
                />
              </div>
            </div>
          )}

          {/* API Deployments */}
          {activeSection === "api-deployments" && (
            <div>
              <h1 className="text-4xl font-bold tracking-tight text-forest-dark">Deployments API</h1>
              <p className="mt-4 text-lg text-forest-dark/70">Create, list, and manage deployments.</p>
              <div className="mt-6 rounded-xl border border-forest/20 bg-forest/5 p-4">
                <p className="text-sm text-forest-dark/70">
                  <Link href="/docs/api" className="text-forest font-medium hover:underline">
                    View full API Reference
                  </Link>
                </p>
              </div>
            </div>
          )}

          {/* API Keys */}
          {activeSection === "api-keys" && (
            <div>
              <h1 className="text-4xl font-bold tracking-tight text-forest-dark">API Keys</h1>
              <p className="mt-4 text-lg text-forest-dark/70">Generate and manage API keys programmatically.</p>
              <div className="mt-6 rounded-xl border border-forest/20 bg-forest/5 p-4">
                <p className="text-sm text-forest-dark/70">
                  <Link href="/docs/api" className="text-forest font-medium hover:underline">
                    View full API Reference
                  </Link>
                </p>
              </div>
            </div>
          )}

          {/* API Usage */}
          {activeSection === "api-usage" && (
            <div>
              <h1 className="text-4xl font-bold tracking-tight text-forest-dark">Usage & Billing</h1>
              <p className="mt-4 text-lg text-forest-dark/70">Track your usage and billing information.</p>
              <div className="mt-6 rounded-xl border border-forest/20 bg-forest/5 p-4">
                <p className="text-sm text-forest-dark/70">
                  <Link href="/docs/api" className="text-forest font-medium hover:underline">
                    View full API Reference
                  </Link>
                </p>
              </div>
            </div>
          )}

          {/* Template: Ollama Chat */}
          {activeSection === "template-ollama" && (
            <div>
              <h1 className="text-4xl font-bold tracking-tight text-forest-dark">Ollama Chat</h1>
              <p className="mt-4 text-lg text-forest-dark/70 leading-relaxed">
                Deploy a fully managed Ollama instance with Open WebUI for conversational AI.
              </p>

              <div className="mt-10 space-y-8">
                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">What&apos;s included</h2>
                  <ul className="mt-4 space-y-2 text-forest-dark/70">
                    <li className="flex items-start gap-2">
                      <svg className="mt-1 h-4 w-4 flex-shrink-0 text-forest" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                      </svg>
                      Ollama inference server with GPU acceleration
                    </li>
                    <li className="flex items-start gap-2">
                      <svg className="mt-1 h-4 w-4 flex-shrink-0 text-forest" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                      </svg>
                      Open WebUI chat interface
                    </li>
                    <li className="flex items-start gap-2">
                      <svg className="mt-1 h-4 w-4 flex-shrink-0 text-forest" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                      </svg>
                      Pre-loaded with Llama 3.2 (3B) model
                    </li>
                    <li className="flex items-start gap-2">
                      <svg className="mt-1 h-4 w-4 flex-shrink-0 text-forest" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                      </svg>
                      OpenAI-compatible API endpoint
                    </li>
                  </ul>
                </div>
                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">Deploy</h2>
                  <CodeBlock code="polaris deploy --template ollama --name my-chat" />
                </div>
                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">Pull additional models</h2>
                  <p className="mt-3 text-forest-dark/70">
                    After deployment, SSH into your instance and pull any Ollama-compatible model.
                  </p>
                  <CodeBlock code={`ssh polaris@<instance-ip>\nollama pull mistral\nollama pull codellama`} />
                </div>
              </div>
            </div>
          )}

          {/* Template: Jupyter Notebook */}
          {activeSection === "template-jupyter" && (
            <div>
              <h1 className="text-4xl font-bold tracking-tight text-forest-dark">Jupyter Notebook</h1>
              <p className="mt-4 text-lg text-forest-dark/70 leading-relaxed">
                Launch a GPU-powered Jupyter environment for data science and machine learning.
              </p>
              <div className="mt-10 space-y-8">
                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">What&apos;s included</h2>
                  <ul className="mt-4 space-y-2 text-forest-dark/70">
                    <li className="flex items-start gap-2">
                      <svg className="mt-1 h-4 w-4 flex-shrink-0 text-forest" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                      </svg>
                      JupyterLab with GPU support
                    </li>
                    <li className="flex items-start gap-2">
                      <svg className="mt-1 h-4 w-4 flex-shrink-0 text-forest" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                      </svg>
                      Pre-installed: PyTorch, TensorFlow, NumPy, Pandas
                    </li>
                    <li className="flex items-start gap-2">
                      <svg className="mt-1 h-4 w-4 flex-shrink-0 text-forest" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                      </svg>
                      Persistent storage across sessions
                    </li>
                  </ul>
                </div>
                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">Deploy</h2>
                  <CodeBlock code="polaris deploy --template jupyter --name my-notebook" />
                </div>
              </div>
            </div>
          )}

          {/* Template: Development Terminal */}
          {activeSection === "template-terminal" && (
            <div>
              <h1 className="text-4xl font-bold tracking-tight text-forest-dark">Development Terminal</h1>
              <p className="mt-4 text-lg text-forest-dark/70 leading-relaxed">
                A full Linux development environment with SSH access and GPU support.
              </p>
              <div className="mt-10 space-y-8">
                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">What&apos;s included</h2>
                  <ul className="mt-4 space-y-2 text-forest-dark/70">
                    <li className="flex items-start gap-2">
                      <svg className="mt-1 h-4 w-4 flex-shrink-0 text-forest" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                      </svg>
                      Ubuntu 22.04 with CUDA drivers
                    </li>
                    <li className="flex items-start gap-2">
                      <svg className="mt-1 h-4 w-4 flex-shrink-0 text-forest" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                      </svg>
                      SSH and web terminal access
                    </li>
                    <li className="flex items-start gap-2">
                      <svg className="mt-1 h-4 w-4 flex-shrink-0 text-forest" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                      </svg>
                      Docker, Git, Node.js, Python pre-installed
                    </li>
                  </ul>
                </div>
                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">Deploy</h2>
                  <CodeBlock code="polaris deploy --template terminal --name my-dev-box" />
                </div>
              </div>
            </div>
          )}

          {/* Template: Cloud Computer */}
          {activeSection === "template-cloud" && (
            <div>
              <h1 className="text-4xl font-bold tracking-tight text-forest-dark">Cloud Computer</h1>
              <p className="mt-4 text-lg text-forest-dark/70 leading-relaxed">
                A full desktop environment in the cloud, accessible from any browser.
              </p>
              <div className="mt-10 space-y-8">
                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">What&apos;s included</h2>
                  <ul className="mt-4 space-y-2 text-forest-dark/70">
                    <li className="flex items-start gap-2">
                      <svg className="mt-1 h-4 w-4 flex-shrink-0 text-forest" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                      </svg>
                      Ubuntu Desktop with GPU acceleration
                    </li>
                    <li className="flex items-start gap-2">
                      <svg className="mt-1 h-4 w-4 flex-shrink-0 text-forest" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                      </svg>
                      Browser-based VNC access
                    </li>
                    <li className="flex items-start gap-2">
                      <svg className="mt-1 h-4 w-4 flex-shrink-0 text-forest" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                      </svg>
                      VS Code, Firefox, file manager pre-installed
                    </li>
                  </ul>
                </div>
                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">Deploy</h2>
                  <CodeBlock code="polaris deploy --template cloud-desktop --name my-desktop" />
                </div>
              </div>
            </div>
          )}

          {/* Template: Game Servers */}
          {activeSection === "template-games" && (
            <div>
              <h1 className="text-4xl font-bold tracking-tight text-forest-dark">Game Servers</h1>
              <p className="mt-4 text-lg text-forest-dark/70 leading-relaxed">
                Deploy dedicated game servers with low-latency networking.
              </p>
              <div className="mt-10 space-y-8">
                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">Available games</h2>
                  <ul className="mt-4 space-y-2 text-forest-dark/70">
                    <li className="flex items-start gap-2">
                      <svg className="mt-1 h-4 w-4 flex-shrink-0 text-forest" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                      </svg>
                      Minecraft (Java & Bedrock)
                    </li>
                    <li className="flex items-start gap-2">
                      <svg className="mt-1 h-4 w-4 flex-shrink-0 text-forest" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                      </svg>
                      Valheim
                    </li>
                    <li className="flex items-start gap-2">
                      <svg className="mt-1 h-4 w-4 flex-shrink-0 text-forest" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                      </svg>
                      More coming soon
                    </li>
                  </ul>
                </div>
                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">Deploy</h2>
                  <CodeBlock code="polaris deploy --template minecraft --name my-server" />
                </div>
              </div>
            </div>
          )}

          {/* Guide: Deploy Your First Model */}
          {activeSection === "guide-deploy" && (
            <div>
              <h1 className="text-4xl font-bold tracking-tight text-forest-dark">
                Deploy Your First Model
              </h1>
              <p className="mt-4 text-lg text-forest-dark/70 leading-relaxed">
                A step-by-step guide to deploying an AI model on Polaris Computer.
              </p>

              <div className="mt-12 space-y-10">
                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">1. Choose a template</h2>
                  <p className="mt-3 text-forest-dark/70">
                    List all available templates to find the right one for your use case.
                  </p>
                  <CodeBlock code="polaris templates list" />
                </div>

                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">2. Deploy the template</h2>
                  <p className="mt-3 text-forest-dark/70">
                    Deploy with a name that helps you identify the instance later.
                  </p>
                  <CodeBlock code="polaris deploy --template ollama --name production-llm" />
                </div>

                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">3. Monitor the deployment</h2>
                  <p className="mt-3 text-forest-dark/70">
                    Check deployment status. It typically takes 1-2 minutes for the instance to become ready.
                  </p>
                  <CodeBlock code="polaris instances list" />
                </div>

                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">4. Access your model</h2>
                  <p className="mt-3 text-forest-dark/70">
                    Once running, access your model via the provided URL or SSH.
                  </p>
                  <CodeBlock
                    code={`# Via the web UI (shown in instance details)
polaris instances list

# Via the API
curl https://<your-instance>.polaris.computer/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -d '{"model": "llama3.2", "messages": [{"role": "user", "content": "Hello!"}]}'`}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Guide: SSH Access */}
          {activeSection === "guide-ssh" && (
            <div>
              <h1 className="text-4xl font-bold tracking-tight text-forest-dark">SSH Access</h1>
              <p className="mt-4 text-lg text-forest-dark/70 leading-relaxed">
                Connect to your Polaris instances via SSH for full terminal access.
              </p>

              <div className="mt-10 space-y-8">
                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">Connect to an instance</h2>
                  <p className="mt-3 text-forest-dark/70">
                    Use the SSH details from your instance&apos;s dashboard or the CLI.
                  </p>
                  <CodeBlock code="ssh polaris@<instance-ip> -p 22" />
                </div>

                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">SSH key setup</h2>
                  <p className="mt-3 text-forest-dark/70">
                    Add your SSH public key to your Polaris account for passwordless access.
                  </p>
                  <CodeBlock
                    code={`# Copy your public key
cat ~/.ssh/id_rsa.pub

# Add it to your Polaris account
polaris ssh-keys add --key "$(cat ~/.ssh/id_rsa.pub)"`}
                  />
                </div>

                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">Port forwarding</h2>
                  <p className="mt-3 text-forest-dark/70">
                    Forward ports from your instance to access services locally.
                  </p>
                  <CodeBlock code="ssh -L 8080:localhost:8080 polaris@<instance-ip>" />
                </div>
              </div>
            </div>
          )}

          {/* Guide: API Key Management */}
          {activeSection === "guide-api-keys" && (
            <div>
              <h1 className="text-4xl font-bold tracking-tight text-forest-dark">
                API Key Management
              </h1>
              <p className="mt-4 text-lg text-forest-dark/70 leading-relaxed">
                Create, manage, and secure your Polaris API keys.
              </p>

              <div className="mt-10 space-y-8">
                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">Generate a key</h2>
                  <p className="mt-3 text-forest-dark/70">
                    Create a named API key for each application or environment.
                  </p>
                  <CodeBlock code="polaris keys generate --name production-api" />
                </div>

                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">List your keys</h2>
                  <CodeBlock code="polaris keys list" />
                </div>

                <div>
                  <h2 className="text-2xl font-semibold text-forest-dark">Revoke a key</h2>
                  <p className="mt-3 text-forest-dark/70">
                    Revoke a compromised or unused key immediately.
                  </p>
                  <CodeBlock code="polaris keys revoke <key-id>" />
                </div>

                <div className="rounded-xl border border-copper/30 bg-copper/5 p-6">
                  <h3 className="text-sm font-semibold text-copper">Security best practices</h3>
                  <ul className="mt-3 space-y-2 text-sm text-forest-dark/70">
                    <li>Never commit API keys to version control</li>
                    <li>Use environment variables to store keys</li>
                    <li>Rotate keys regularly</li>
                    <li>Use separate keys for development and production</li>
                    <li>Revoke keys immediately if compromised</li>
                  </ul>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Footer */}
      <footer className="border-t border-mist px-8 py-6 text-center text-sm text-forest-dark/50">
        Polaris Computer
      </footer>
    </div>
  );
}
