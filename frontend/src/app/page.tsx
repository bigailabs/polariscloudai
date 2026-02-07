export const dynamic = "force-dynamic";

import Link from "next/link";
import { SignedIn, SignedOut } from "@clerk/nextjs";

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
        </nav>
      </header>

      <main className="flex flex-1 flex-col items-center justify-center px-8 py-24">
        <div className="max-w-2xl text-center">
          <h1 className="text-5xl font-bold tracking-tight text-forest-dark leading-tight">
            Deploy AI models
            <br />
            in seconds
          </h1>
          <p className="mt-6 text-lg text-forest-dark/70 leading-relaxed max-w-lg mx-auto">
            GPU-powered cloud compute with pre-built templates. From text generation to image synthesis — launch production-ready AI with one click.
          </p>
          <div className="mt-10 flex items-center justify-center gap-4">
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
              href="/sign-in"
              className="rounded-lg border border-forest/20 px-6 py-3 text-base font-medium text-forest-dark hover:border-forest/40 transition-colors"
            >
              Learn more
            </Link>
          </div>
        </div>
      </main>

      <footer className="border-t border-mist px-8 py-6 text-center text-sm text-forest-dark/50">
        Polaris Computer
      </footer>
    </div>
  );
}
