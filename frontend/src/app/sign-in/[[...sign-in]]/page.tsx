import { SignIn } from "@clerk/nextjs";
import Link from "next/link";
import { AT_CAPACITY } from "@/lib/config";

export default function SignInPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-sage">
      <div className="flex flex-col items-center gap-4">
        {AT_CAPACITY && (
          <div className="inline-flex rounded-lg bg-forest/10 px-4 py-2 text-sm text-forest-dark">
            New signups are paused while we scale infrastructure. Existing users
            can sign in as usual.
          </div>
        )}

        <SignIn
          appearance={{
            elements: {
              rootBox: "mx-auto",
              card: "shadow-lg border border-mist",
            },
          }}
        />

        {AT_CAPACITY && (
          <p className="text-sm text-forest-dark/60">
            Don&apos;t have an account?{" "}
            <Link
              href="/sign-up"
              className="font-medium text-forest hover:text-forest-hover"
            >
              Join the waitlist &rarr;
            </Link>
          </p>
        )}
      </div>
    </div>
  );
}
