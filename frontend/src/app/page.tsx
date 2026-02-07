export const dynamic = "force-dynamic";

import Link from "next/link";
import { SignedIn, SignedOut } from "@clerk/nextjs";
import { AT_CAPACITY } from "@/lib/config";
import { WaitlistForm } from "@/components/waitlist-form";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex items-center justify-between px-8 py-4 border-b border-mist">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-forest flex items-center justify-center">
            <span className="text-white font-bold text-sm">P</span>
          </div>
          <span className="text-lg font-semibold text-forest-dark">
            Polaris Computer
          </span>
        </div>
        <nav className="flex items-center gap-4">
          <Link
            href="/docs"
            className="text-sm font-medium text-forest-dark hover:text-forest transition-colors"
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
              Deploy AI models
              <br />
              in seconds
            </h1>
            <p className="mt-6 text-lg text-forest-dark/70 leading-relaxed max-w-lg mx-auto">
              {AT_CAPACITY
                ? "Fast, reliable inference API for production workloads. GPU-powered endpoints for text generation, image synthesis, and more."
                : "GPU-powered cloud compute with pre-built templates. From text generation to image synthesis \u2014 launch production-ready AI with one click."}
            </p>
            <div className="mt-10 flex items-center justify-center gap-4">
              {AT_CAPACITY ? (
                <>
                  <SignedOut>
                    <a
                      href="#waitlist"
                      className="rounded-lg bg-forest px-6 py-3 text-base font-medium text-white hover:bg-forest-hover transition-colors"
                    >
                      Join the waitlist
                    </a>
                  </SignedOut>
                  <SignedIn>
                    <Link
                      href="/dashboard"
                      className="rounded-lg bg-forest px-6 py-3 text-base font-medium text-white hover:bg-forest-hover transition-colors"
                    >
                      Go to dashboard
                    </Link>
                  </SignedIn>
                  <Link
                    href="/pricing"
                    className="rounded-lg border border-forest/20 px-6 py-3 text-base font-medium text-forest-dark hover:border-forest/40 transition-colors"
                  >
                    Learn more
                  </Link>
                </>
              ) : (
                <>
                  <SignedOut>
                    <Link
                      href="/sign-up"
                      className="rounded-lg bg-forest px-6 py-3 text-base font-medium text-white hover:bg-forest-hover transition-colors"
                    >
                      Start deploying
                    </Link>
                  </SignedOut>
                  <SignedIn>
                    <Link
                      href="/dashboard"
                      className="rounded-lg bg-forest px-6 py-3 text-base font-medium text-white hover:bg-forest-hover transition-colors"
                    >
                      Go to dashboard
                    </Link>
                  </SignedIn>
                  <Link
                    href="/pricing"
                    className="rounded-lg border border-forest/20 px-6 py-3 text-base font-medium text-forest-dark hover:border-forest/40 transition-colors"
                  >
                    Learn more
                  </Link>
                </>
              )}
            </div>
          </div>
        </section>

        {/* CLI Terminal Demo */}
        <section className="flex justify-center px-8 pb-16">
          <div className="w-full max-w-2xl">
            <div className="rounded-xl border border-forest-dark/10 bg-forest-dark overflow-hidden shadow-lg">
              <div className="flex items-center gap-2 px-4 py-3 bg-forest-dark/80 border-b border-white/5">
                <div className="h-3 w-3 rounded-full bg-red-400/80" />
                <div className="h-3 w-3 rounded-full bg-yellow-400/80" />
                <div className="h-3 w-3 rounded-full bg-green-400/80" />
                <span className="ml-2 text-xs text-white/40 font-mono">terminal</span>
              </div>
              <div className="p-5 font-mono text-sm leading-relaxed">
                <div className="text-white/60">
                  <span className="text-green-400">$</span>{" "}
                  <span className="text-white">polaris deploy --template ollama --name my-llm</span>
                </div>
                <div className="mt-3 text-white/50">Deploying Ollama Chat...</div>
                <div className="text-white/50">
                  &nbsp;&nbsp;Template: Ollama + Open WebUI
                </div>
                <div className="text-white/50">
                  &nbsp;&nbsp;Model: &nbsp;&nbsp; llama3.2 (3B)
                </div>
                <div className="text-white/50">
                  &nbsp;&nbsp;Region: &nbsp; Lagos, Nigeria
                </div>
                <div className="mt-3 text-green-400">
                  &#10003; Deployment created!
                </div>
                <div className="mt-3 text-white/60">
                  <span className="text-green-400">$</span>{" "}
                  <span className="text-white">polaris instances list</span>
                </div>
                <div className="mt-2 text-white/40 text-xs">
                  <div>ID &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Name &nbsp;&nbsp;&nbsp;&nbsp; Template &nbsp; Status</div>
                  <div>a7f3b291 &nbsp;my-llm &nbsp;&nbsp; ollama &nbsp;&nbsp;&nbsp; <span className="text-green-400">running</span></div>
                </div>
                <div className="mt-3 text-white/60">
                  <span className="text-green-400">$</span>{" "}
                  <span className="text-white/40 animate-pulse">_</span>
                </div>
              </div>
            </div>
            <p className="mt-3 text-center text-xs text-forest-dark/60">
              Install: npm install -g @polaris-cloud/cli
            </p>
          </div>
        </section>

        {/* Capacity Banner */}
        {AT_CAPACITY && (
          <section
            id="waitlist"
            className="bg-sage border-y border-mist px-8 py-20"
          >
            <div className="max-w-2xl mx-auto text-center">
              <span className="inline-block rounded-full bg-copper/10 px-3 py-1 text-xs font-semibold tracking-wide text-copper uppercase">
                At capacity
              </span>
              <h2 className="mt-6 text-3xl font-bold tracking-tight text-forest-dark">
                We&apos;re scaling responsibly
              </h2>
              <p className="mt-4 text-base text-forest-dark/70 leading-relaxed max-w-lg mx-auto">
                To ensure fast, reliable inference for every user, we&apos;re
                temporarily limiting new signups. Join the waitlist and
                we&apos;ll open a spot as soon as we can guarantee the
                experience you deserve.
              </p>
              <p className="mt-3 text-sm text-forest-dark/50">
                Already have an account? API keys are available from your{" "}
                <Link
                  href="/dashboard"
                  className="underline hover:text-forest transition-colors"
                >
                  dashboard
                </Link>
                .
              </p>
              <div className="mt-8">
                <WaitlistForm variant="hero" />
              </div>
            </div>
          </section>
        )}
      </main>

      <footer className="border-t border-mist px-8 py-6">
        <div className="flex items-center justify-between text-sm text-forest-dark/50">
          <span>Polaris Computer</span>
          <div className="flex items-center gap-4">
            <Link
              href="/pricing"
              className="hover:text-forest transition-colors"
            >
              Pricing
            </Link>
            <Link
              href="/status"
              className="hover:text-forest transition-colors"
            >
              Status
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
