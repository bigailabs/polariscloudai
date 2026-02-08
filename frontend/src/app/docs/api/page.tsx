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

function MethodBadge({ method }: { method: string }) {
  const colors: Record<string, string> = {
    GET: "bg-fern/15 text-fern",
    POST: "bg-forest/15 text-forest",
    DELETE: "bg-red-500/15 text-red-600",
    PUT: "bg-copper/15 text-copper",
    PATCH: "bg-copper/15 text-copper",
  };

  return (
    <span className={`inline-flex rounded-md px-2 py-0.5 text-xs font-bold font-mono ${colors[method] || "bg-gray-100 text-gray-600"}`}>
      {method}
    </span>
  );
}

interface Endpoint {
  method: string;
  path: string;
  description: string;
  auth: boolean;
  requestBody?: string;
  responseExample: string;
}

const endpointGroups: {
  title: string;
  slug: string;
  description: string;
  endpoints: Endpoint[];
}[] = [
  {
    title: "Inference",
    slug: "inference",
    description: "OpenAI-compatible chat completions API. Use your API key to run inference on open-source models.",
    endpoints: [
      {
        method: "GET",
        path: "/v1/models",
        description: "List all available models. No authentication required.",
        auth: false,
        responseExample: `{
  "object": "list",
  "data": [
    { "id": "llama-3.3-70b", "object": "model", "owned_by": "meta", "context_window": 8192 },
    { "id": "llama-3.1-8b", "object": "model", "owned_by": "meta", "context_window": 131072 },
    { "id": "llama-3.3-70b-versatile", "object": "model", "owned_by": "meta", "context_window": 131072 },
    { "id": "mixtral-8x7b", "object": "model", "owned_by": "mistral", "context_window": 32768 },
    { "id": "gemma2-9b", "object": "model", "owned_by": "google", "context_window": 8192 },
    { "id": "deepseek-r1-70b", "object": "model", "owned_by": "deepseek", "context_window": 131072 }
  ]
}`,
      },
      {
        method: "POST",
        path: "/v1/chat/completions",
        description: "Create a chat completion. Supports streaming via SSE. Compatible with the OpenAI SDK — just change the base URL and API key.",
        auth: true,
        requestBody: `{
  "model": "llama-3.1-8b",
  "messages": [
    { "role": "user", "content": "Explain quantum computing in one sentence." }
  ],
  "stream": false
}`,
        responseExample: `{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "model": "llama-3.1-8b",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Quantum computing uses qubits that can exist in superposition..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 14,
    "completion_tokens": 28,
    "total_tokens": 42
  }
}`,
      },
    ],
  },
  {
    title: "API Keys",
    slug: "api-keys",
    description: "Generate and manage API keys for inference access. Requires dashboard authentication (Clerk).",
    endpoints: [
      {
        method: "GET",
        path: "/api/keys",
        description: "List all API keys for the authenticated user. Key values are masked — only the prefix is returned.",
        auth: true,
        responseExample: `[
  {
    "id": "a7f3b291-...",
    "name": "production-api",
    "key_prefix": "pi_sk_8a3f12",
    "request_count": 1420,
    "is_active": true,
    "created_at": "2026-01-15T10:00:00Z",
    "last_used_at": "2026-02-08T06:00:00Z"
  }
]`,
      },
      {
        method: "POST",
        path: "/api/keys/generate",
        description: "Generate a new API key. The full key is returned only once — store it securely.",
        auth: true,
        requestBody: `{
  "name": "production-api"
}`,
        responseExample: `{
  "id": "a7f3b291-...",
  "key": "pi_sk_8a3f12b9c4e5d6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0"
}`,
      },
      {
        method: "DELETE",
        path: "/api/keys/{id}",
        description: "Revoke an API key. The key is soft-deleted and any future requests using it will be rejected.",
        auth: true,
        responseExample: `{
  "success": true
}`,
      },
    ],
  },
  {
    title: "Usage",
    slug: "usage",
    description: "Track inference API consumption.",
    endpoints: [
      {
        method: "GET",
        path: "/api/usage",
        description: "Retrieve inference usage statistics for the current billing period, including request counts, token usage, and model breakdown.",
        auth: true,
        responseExample: `{
  "period": "2026-02",
  "total_requests": 1420,
  "total_input_tokens": 284000,
  "total_output_tokens": 142000,
  "by_model": [
    { "model": "llama-3.1-8b", "requests": 1100, "input_tokens": 220000, "output_tokens": 110000 },
    { "model": "llama-3.3-70b", "requests": 320, "input_tokens": 64000, "output_tokens": 32000 }
  ]
}`,
      },
    ],
  },
];

const sidebarItems = [
  { label: "Overview", slug: "overview" },
  { label: "Authentication", slug: "auth-section" },
  { label: "Base URL", slug: "base-url" },
  { label: "Error Handling", slug: "errors" },
  ...endpointGroups.map((g) => ({
    label: g.title,
    slug: g.slug,
  })),
];

export default function APIReferencePage() {
  const [activeSection, setActiveSection] = useState("overview");
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
              API Reference
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
          {/* Overview */}
          <section id="overview">
            <h1 className="text-4xl font-bold tracking-tight text-forest-dark">
              API Reference
            </h1>
            <p className="mt-4 text-lg text-forest-dark/70 leading-relaxed">
              The Polaris inference API is OpenAI-compatible. Use your API key to run open-source models with a single line of code.
            </p>
          </section>

          {/* Base URL */}
          <section id="base-url" className="mt-12 scroll-mt-8">
            <h2 className="text-2xl font-semibold text-forest-dark border-b border-mist pb-3">
              Base URL
            </h2>
            <p className="mt-4 text-forest-dark/70">
              All inference requests use the following base URL:
            </p>
            <CodeBlock code="https://polaris.computer/v1" language="text" />
          </section>

          {/* Authentication */}
          <section id="auth-section" className="mt-12 scroll-mt-8">
            <h2 className="text-2xl font-semibold text-forest-dark border-b border-mist pb-3">
              Authentication
            </h2>
            <p className="mt-4 text-forest-dark/70">
              Authenticate requests by including your API key in the <code className="rounded bg-forest-dark/10 px-1.5 py-0.5 text-sm font-mono text-forest-dark">Authorization</code> header as a Bearer token.
            </p>
            <CodeBlock
              code={`curl https://polaris.computer/v1/chat/completions \\
  -H "Authorization: Bearer pi_sk_your_key_here" \\
  -H "Content-Type: application/json" \\
  -d '{"model": "llama-3.1-8b", "messages": [{"role": "user", "content": "Hello"}]}'`}
            />
            <p className="mt-4 text-sm text-forest-dark/60">
              API keys are prefixed with <code className="rounded bg-forest-dark/10 px-1.5 py-0.5 text-xs font-mono text-forest-dark">pi_sk_</code>. Generate keys from your{" "}
              <Link href="/dashboard/api-keys" className="text-forest hover:underline">dashboard</Link>.
            </p>

            <h3 className="mt-8 text-lg font-semibold text-forest-dark">OpenAI SDK</h3>
            <p className="mt-2 text-sm text-forest-dark/70">
              Works with the OpenAI Python and Node SDKs — just change the base URL:
            </p>
            <CodeBlock
              code={`from openai import OpenAI

client = OpenAI(
    base_url="https://polaris.computer/v1",
    api_key="pi_sk_your_key_here"
)

response = client.chat.completions.create(
    model="llama-3.1-8b",
    messages=[{"role": "user", "content": "Hello"}]
)
print(response.choices[0].message.content)`}
              language="python"
            />
          </section>

          {/* Error Handling */}
          <section id="errors" className="mt-12 scroll-mt-8">
            <h2 className="text-2xl font-semibold text-forest-dark border-b border-mist pb-3">
              Error Handling
            </h2>
            <p className="mt-4 text-forest-dark/70">
              The API uses standard HTTP status codes to indicate the success or failure of a request.
            </p>
            <div className="mt-6 overflow-hidden rounded-xl border border-mist">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-mist bg-stone">
                    <th className="px-4 py-3 text-left text-sm font-semibold text-forest-dark">Status</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-forest-dark">Meaning</th>
                  </tr>
                </thead>
                <tbody className="text-sm">
                  {[
                    ["200", "OK - Request succeeded"],
                    ["201", "Created - Resource created successfully"],
                    ["400", "Bad Request - Invalid parameters"],
                    ["401", "Unauthorized - Missing or invalid API key"],
                    ["403", "Forbidden - Insufficient permissions"],
                    ["404", "Not Found - Resource does not exist"],
                    ["429", "Rate Limited - Too many requests"],
                    ["500", "Server Error - Something went wrong on our end"],
                  ].map(([code, desc]) => (
                    <tr key={code} className="border-b border-mist last:border-b-0">
                      <td className="px-4 py-3 font-mono text-xs text-forest">{code}</td>
                      <td className="px-4 py-3 text-forest-dark/70">{desc}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-4 text-sm text-forest-dark/60">Error response format:</p>
            <CodeBlock
              code={`{
  "error": {
    "code": "unauthorized",
    "message": "Invalid or expired API key"
  }
}`}
              language="json"
            />
          </section>

          {/* Endpoint Groups */}
          {endpointGroups.map((group) => (
            <section key={group.slug} id={group.slug} className="mt-16 scroll-mt-8">
              <h2 className="text-2xl font-semibold text-forest-dark border-b border-mist pb-3">
                {group.title}
              </h2>
              <p className="mt-4 text-forest-dark/70">{group.description}</p>

              {group.endpoints.map((endpoint) => (
                <div
                  key={`${endpoint.method}-${endpoint.path}`}
                  className="mt-8 rounded-xl border border-mist overflow-hidden"
                >
                  {/* Endpoint header */}
                  <div className="flex items-center gap-3 px-6 py-4 bg-stone border-b border-mist">
                    <MethodBadge method={endpoint.method} />
                    <code className="text-sm font-mono text-forest-dark font-medium">
                      {endpoint.path}
                    </code>
                    {endpoint.auth && (
                      <span className="ml-auto rounded-full bg-forest/10 px-2.5 py-0.5 text-xs font-medium text-forest">
                        Auth required
                      </span>
                    )}
                  </div>

                  {/* Endpoint body */}
                  <div className="p-6">
                    <p className="text-sm text-forest-dark/70">{endpoint.description}</p>

                    {endpoint.requestBody && (
                      <div className="mt-6">
                        <h4 className="text-sm font-semibold text-forest-dark/80 uppercase tracking-wider mb-2">
                          Request body
                        </h4>
                        <CodeBlock code={endpoint.requestBody} language="json" />
                      </div>
                    )}

                    <div className="mt-6">
                      <h4 className="text-sm font-semibold text-forest-dark/80 uppercase tracking-wider mb-2">
                        Response example
                      </h4>
                      <CodeBlock code={endpoint.responseExample} language="json" />
                    </div>

                    {/* cURL example */}
                    <div className="mt-6">
                      <h4 className="text-sm font-semibold text-forest-dark/80 uppercase tracking-wider mb-2">
                        Example request
                      </h4>
                      <CodeBlock
                        code={
                          endpoint.method === "GET"
                            ? `curl https://polaris.computer${endpoint.path.replace("{id}", "example_id")}${endpoint.auth ? ' \\\n  -H "Authorization: Bearer pi_sk_your_key_here"' : ""}`
                            : endpoint.method === "POST"
                              ? `curl -X POST https://polaris.computer${endpoint.path} \\\n  -H "Authorization: Bearer pi_sk_your_key_here" \\\n  -H "Content-Type: application/json" \\\n  -d '${endpoint.requestBody || "{}"}'`
                              : `curl -X DELETE https://polaris.computer${endpoint.path.replace("{id}", "example_id")} \\\n  -H "Authorization: Bearer pi_sk_your_key_here"`
                        }
                      />
                    </div>
                  </div>
                </div>
              ))}
            </section>
          ))}

          {/* Rate Limits */}
          <section className="mt-16 scroll-mt-8">
            <h2 className="text-2xl font-semibold text-forest-dark border-b border-mist pb-3">
              Rate Limits
            </h2>
            <p className="mt-4 text-forest-dark/70">
              Rate limits are applied per API key. When you exceed the limit, requests return a <code className="rounded bg-forest-dark/10 px-1.5 py-0.5 text-sm font-mono text-forest-dark">429</code> status code with a <code className="rounded bg-forest-dark/10 px-1.5 py-0.5 text-sm font-mono text-forest-dark">Retry-After</code> header.
            </p>
            <div className="mt-6 overflow-hidden rounded-xl border border-mist">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-mist bg-stone">
                    <th className="px-4 py-3 text-left text-sm font-semibold text-forest-dark">Limit</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-forest-dark">Value</th>
                  </tr>
                </thead>
                <tbody className="text-sm">
                  {[
                    ["Requests per minute", "60"],
                    ["Requests per day", "1,000"],
                  ].map(([limit, value]) => (
                    <tr key={limit} className="border-b border-mist last:border-b-0">
                      <td className="px-4 py-3 text-forest-dark">{limit}</td>
                      <td className="px-4 py-3 font-mono text-forest-dark/70">{value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-4 text-sm text-forest-dark/60">
              Rate limit headers are included in every response:{" "}
              <code className="rounded bg-forest-dark/10 px-1 py-0.5 text-xs font-mono text-forest-dark">X-RateLimit-Limit</code>,{" "}
              <code className="rounded bg-forest-dark/10 px-1 py-0.5 text-xs font-mono text-forest-dark">X-RateLimit-Remaining</code>,{" "}
              <code className="rounded bg-forest-dark/10 px-1 py-0.5 text-xs font-mono text-forest-dark">X-RateLimit-Reset</code>.
            </p>
          </section>

          {/* Models */}
          <section className="mt-16 mb-16 scroll-mt-8">
            <h2 className="text-2xl font-semibold text-forest-dark border-b border-mist pb-3">
              Available Models
            </h2>
            <div className="mt-6 overflow-hidden rounded-xl border border-mist">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-mist bg-stone">
                    <th className="px-4 py-3 text-left text-sm font-semibold text-forest-dark">Model ID</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-forest-dark">Provider</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-forest-dark">Context</th>
                  </tr>
                </thead>
                <tbody className="text-sm">
                  {[
                    ["llama-3.3-70b", "Meta", "8K"],
                    ["llama-3.1-8b", "Meta", "128K"],
                    ["llama-3.3-70b-versatile", "Meta", "128K"],
                    ["mixtral-8x7b", "Mistral", "32K"],
                    ["gemma2-9b", "Google", "8K"],
                    ["deepseek-r1-70b", "DeepSeek", "128K"],
                  ].map(([id, provider, ctx]) => (
                    <tr key={id} className="border-b border-mist last:border-b-0">
                      <td className="px-4 py-3 font-mono text-xs text-forest">{id}</td>
                      <td className="px-4 py-3 text-forest-dark/70">{provider}</td>
                      <td className="px-4 py-3 text-forest-dark/70">{ctx}</td>
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
