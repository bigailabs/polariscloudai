import Link from "next/link";
import { SignedIn, SignedOut } from "@clerk/nextjs";
import { AT_CAPACITY } from "@/lib/config";
import { WaitlistForm } from "@/components/waitlist-form";

const tiers = [
  {
    name: "Hobby",
    price: "$9",
    period: "/mo",
    description: "For side projects and experimentation",
    features: [
      "5,000 requests/day",
      "All models (rate limited)",
      "Community support",
      "API key access",
    ],
    cta: AT_CAPACITY ? "Join Waitlist" : "Get Started",
    ctaHref: AT_CAPACITY ? "#waitlist" : "/sign-up",
    style: "default" as const,
  },
  {
    name: "Starter",
    price: "$49",
    period: "/mo",
    description: "For indie developers and small teams",
    badge: "Popular",
    features: [
      "50,000 requests/day",
      "Priority model access",
      "Email support",
      "API key access",
      "Faster rate limits",
    ],
    cta: AT_CAPACITY ? "Join Waitlist" : "Start Building",
    ctaHref: AT_CAPACITY ? "#waitlist" : "/sign-up",
    style: "popular" as const,
  },
  {
    name: "Pro",
    price: "$199",
    period: "/mo",
    description: "For production workloads at scale",
    features: [
      "Unlimited requests",
      "Dedicated throughput",
      "Priority support + SLA",
      "API key access",
      "Custom rate limits",
      "Webhooks & analytics",
    ],
    cta: AT_CAPACITY ? "Join Waitlist" : "Go Pro",
    ctaHref: AT_CAPACITY ? "#waitlist" : "/sign-up",
    style: "default" as const,
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "",
    description: "For organizations with advanced needs",
    features: [
      "Volume pricing",
      "Dedicated infrastructure",
      "24/7 support + SLA",
      "Custom models & fine-tuning",
      "SSO & team management",
      "On-prem deployment options",
    ],
    cta: "Contact Sales",
    ctaHref: "mailto:sales@polaris.computer",
    style: "enterprise" as const,
  },
];

const models = [
  {
    name: "Llama 3.3 70B",
    input: "$0.59",
    output: "$0.79",
    speed: "Fast",
  },
  {
    name: "Llama 3.1 8B",
    input: "$0.05",
    output: "$0.08",
    speed: "Fastest",
  },
  {
    name: "Llama 3.3 70B Versatile",
    input: "$0.59",
    output: "$0.79",
    speed: "Fast",
  },
  {
    name: "Mixtral 8x7B",
    input: "$0.24",
    output: "$0.24",
    speed: "Fast",
  },
  {
    name: "Gemma 2 9B",
    input: "$0.20",
    output: "$0.20",
    speed: "Fast",
  },
  {
    name: "DeepSeek R1 (Distill 70B)",
    input: "$0.75",
    output: "$0.99",
    speed: "Fast",
  },
];

export default function PricingPage() {
  return (
    <div className="flex min-h-screen flex-col">
      {/* Navbar */}
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
            className="text-sm font-medium text-forest-dark hover:text-forest transition-colors"
          >
            Docs
          </Link>
          <Link
            href="/pricing"
            className="text-sm font-medium text-forest transition-colors"
          >
            Pricing
          </Link>
          {AT_CAPACITY ? (
            <>
              <SignedOut>
                <a
                  href="#waitlist"
                  className="rounded-lg bg-forest px-4 py-2 text-sm font-medium text-white hover:bg-forest-hover transition-colors"
                >
                  Join Waitlist
                </a>
              </SignedOut>
              <SignedIn>
                <Link
                  href="/dashboard"
                  className="rounded-lg bg-forest px-4 py-2 text-sm font-medium text-white hover:bg-forest-hover transition-colors"
                >
                  Dashboard
                </Link>
              </SignedIn>
            </>
          ) : (
            <>
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
              <SignedIn>
                <Link
                  href="/dashboard"
                  className="rounded-lg bg-forest px-4 py-2 text-sm font-medium text-white hover:bg-forest-hover transition-colors"
                >
                  Dashboard
                </Link>
              </SignedIn>
            </>
          )}
        </nav>
      </header>

      <main className="flex flex-1 flex-col">
        {/* Hero */}
        <section className="flex flex-col items-center justify-center px-8 py-24">
          <div className="max-w-2xl text-center">
            <h1 className="text-5xl font-bold tracking-tight text-forest-dark leading-tight">
              Simple, transparent pricing
            </h1>
            <p className="mt-6 text-lg text-forest-dark/70 leading-relaxed max-w-xl mx-auto">
              Pay only for what you use. Every plan includes access to the full
              model catalog, API keys, and our inference infrastructure.
            </p>
          </div>
        </section>

        {/* Pricing Tiers */}
        <section className="px-8 pb-24">
          <div className="mx-auto max-w-6xl grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {tiers.map((tier) => (
              <div
                key={tier.name}
                className={`relative flex flex-col rounded-xl p-8 ${
                  tier.style === "popular"
                    ? "border-2 border-forest bg-forest/5"
                    : tier.style === "enterprise"
                      ? "bg-forest-dark text-white"
                      : "border border-mist bg-white"
                }`}
              >
                {tier.badge && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-forest px-3 py-1 text-xs font-semibold text-white">
                    {tier.badge}
                  </span>
                )}

                <div className="mb-6">
                  <h3
                    className={`text-lg font-semibold ${
                      tier.style === "enterprise"
                        ? "text-white"
                        : "text-forest-dark"
                    }`}
                  >
                    {tier.name}
                  </h3>
                  <div className="mt-3 flex items-baseline gap-1">
                    <span
                      className={`text-4xl font-bold tracking-tight ${
                        tier.style === "enterprise"
                          ? "text-white"
                          : "text-forest-dark"
                      }`}
                    >
                      {tier.price}
                    </span>
                    {tier.period && (
                      <span
                        className={`text-sm ${
                          tier.style === "enterprise"
                            ? "text-white/60"
                            : "text-forest-dark/50"
                        }`}
                      >
                        {tier.period}
                      </span>
                    )}
                  </div>
                  <p
                    className={`mt-2 text-sm ${
                      tier.style === "enterprise"
                        ? "text-white/70"
                        : "text-forest-dark/60"
                    }`}
                  >
                    {tier.description}
                  </p>
                </div>

                <ul className="mb-8 flex-1 space-y-3">
                  {tier.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2">
                      <svg
                        className={`mt-0.5 h-4 w-4 flex-shrink-0 ${
                          tier.style === "enterprise"
                            ? "text-fern"
                            : "text-forest"
                        }`}
                        fill="none"
                        viewBox="0 0 24 24"
                        strokeWidth={2.5}
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M4.5 12.75l6 6 9-13.5"
                        />
                      </svg>
                      <span
                        className={`text-sm ${
                          tier.style === "enterprise"
                            ? "text-white/80"
                            : "text-forest-dark/70"
                        }`}
                      >
                        {feature}
                      </span>
                    </li>
                  ))}
                </ul>

                {tier.style === "enterprise" ? (
                  <a
                    href={tier.ctaHref}
                    className="block w-full rounded-lg border border-white/20 bg-white/10 px-4 py-3 text-center text-sm font-medium text-white hover:bg-white/20 transition-colors"
                  >
                    {tier.cta}
                  </a>
                ) : tier.style === "popular" ? (
                  <Link
                    href={tier.ctaHref}
                    className="block w-full rounded-lg bg-forest px-4 py-3 text-center text-sm font-medium text-white hover:bg-forest-hover transition-colors"
                  >
                    {tier.cta}
                  </Link>
                ) : (
                  <Link
                    href={tier.ctaHref}
                    className="block w-full rounded-lg border border-forest/20 px-4 py-3 text-center text-sm font-medium text-forest-dark hover:border-forest/40 transition-colors"
                  >
                    {tier.cta}
                  </Link>
                )}
              </div>
            ))}
          </div>
        </section>

        {/* Per-Model Token Pricing Table */}
        <section className="bg-sage border-y border-mist px-8 py-24">
          <div className="mx-auto max-w-4xl">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold tracking-tight text-forest-dark">
                Per-model token pricing
              </h2>
              <p className="mt-4 text-base text-forest-dark/70 max-w-lg mx-auto">
                Token-based pricing varies by model. All prices are per 1
                million tokens.
              </p>
            </div>

            <div className="overflow-hidden rounded-xl border border-mist bg-white">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-mist bg-stone">
                    <th className="px-6 py-4 text-left text-sm font-semibold text-forest-dark">
                      Model
                    </th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-forest-dark">
                      Input (per 1M tokens)
                    </th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-forest-dark">
                      Output (per 1M tokens)
                    </th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-forest-dark">
                      Speed
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {models.map((model, i) => (
                    <tr
                      key={model.name}
                      className={`border-b border-mist last:border-b-0 ${
                        i % 2 === 1 ? "bg-sage/50" : "bg-white"
                      }`}
                    >
                      <td className="px-6 py-4 text-sm font-medium text-forest-dark">
                        {model.name}
                      </td>
                      <td className="px-6 py-4 text-sm text-forest-dark/70">
                        {model.input}
                      </td>
                      <td className="px-6 py-4 text-sm text-forest-dark/70">
                        {model.output}
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${
                            model.speed === "Fastest"
                              ? "bg-fern/10 text-fern"
                              : "bg-forest/10 text-forest"
                          }`}
                        >
                          {model.speed}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* API Access Section */}
        <section className="px-8 py-24">
          <div className="mx-auto max-w-4xl">
            <div className="grid gap-12 lg:grid-cols-2 lg:items-center">
              <div>
                <h2 className="text-3xl font-bold tracking-tight text-forest-dark">
                  Built for developers
                </h2>
                <p className="mt-4 text-base text-forest-dark/70 leading-relaxed">
                  Every plan includes API key access. Integrate Polaris
                  inference into your apps with our OpenAI-compatible API.
                </p>
                <ul className="mt-6 space-y-3">
                  {[
                    "OpenAI-compatible endpoints",
                    "Streaming support",
                    "SDKs for Python, Node.js, and more",
                    "Detailed usage analytics",
                  ].map((item) => (
                    <li
                      key={item}
                      className="flex items-center gap-2 text-sm text-forest-dark/70"
                    >
                      <svg
                        className="h-4 w-4 flex-shrink-0 text-forest"
                        fill="none"
                        viewBox="0 0 24 24"
                        strokeWidth={2.5}
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M4.5 12.75l6 6 9-13.5"
                        />
                      </svg>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="rounded-xl bg-forest-dark p-6 overflow-x-auto">
                <pre className="font-mono text-sm leading-relaxed text-white/80">
                  <code>{`curl https://api.polaris.computer/v1/chat/completions \\
  -H "Authorization: Bearer pi_sk_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "llama-3.3-70b",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'`}</code>
                </pre>
              </div>
            </div>
          </div>
        </section>

        {/* Bottom CTA */}
        {AT_CAPACITY ? (
          <section
            id="waitlist"
            className="bg-sage border-y border-mist px-8 py-20"
          >
            <div className="max-w-2xl mx-auto text-center">
              <span className="inline-block rounded-full bg-copper/10 px-3 py-1 text-xs font-semibold tracking-wide text-copper uppercase">
                At capacity
              </span>
              <h2 className="mt-6 text-3xl font-bold tracking-tight text-forest-dark">
                We&apos;re scaling up
              </h2>
              <p className="mt-4 text-base text-forest-dark/70 leading-relaxed max-w-lg mx-auto">
                To ensure fast, reliable inference for every user, we&apos;re
                temporarily limiting new signups. Join the waitlist and
                we&apos;ll let you know when a spot opens.
              </p>
              <div className="mt-8">
                <WaitlistForm variant="hero" />
              </div>
            </div>
          </section>
        ) : (
          <section className="bg-sage border-y border-mist px-8 py-20">
            <div className="max-w-2xl mx-auto text-center">
              <h2 className="text-3xl font-bold tracking-tight text-forest-dark">
                Ready to start?
              </h2>
              <p className="mt-4 text-base text-forest-dark/70 leading-relaxed max-w-lg mx-auto">
                Create a free account and start making API calls in minutes. No
                credit card required.
              </p>
              <div className="mt-8">
                <Link
                  href="/sign-up"
                  className="inline-block rounded-lg bg-forest px-8 py-3 text-base font-medium text-white hover:bg-forest-hover transition-colors"
                >
                  Get Started Free
                </Link>
              </div>
            </div>
          </section>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-mist px-8 py-6 text-center text-sm text-forest-dark/50">
        Polaris Computer
      </footer>
    </div>
  );
}
