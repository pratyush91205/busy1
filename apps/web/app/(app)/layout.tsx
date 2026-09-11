"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { AppHeader } from "@/components/app-header";
import { useCurrentUser } from "@/hooks/use-auth";

/**
 * The shell every signed-in page renders inside.
 *
 * The redirect is a convenience, not a security boundary: it stops a signed-out
 * visitor staring at an empty page, and nothing more. Every endpoint these
 * pages call enforces its own authorization, so bypassing this guard gets you
 * a set of 401s.
 */
export default function AppLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { user, isLoading } = useCurrentUser();

  useEffect(() => {
    if (!isLoading && !user) router.replace("/login");
  }, [isLoading, user, router]);

  // Render nothing rather than the page-with-no-data, and nothing rather than
  // a flash of the login screen for someone who is in fact signed in.
  if (isLoading || !user) {
    return (
      <output
        aria-live="polite"
        className="text-muted-foreground flex min-h-full items-center justify-center text-sm"
      >
        {isLoading ? "Loading…" : "Redirecting to sign in…"}
      </output>
    );
  }

  return (
    <div className="flex min-h-full flex-col">
      <AppHeader user={user} />
      <div className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">{children}</div>
    </div>
  );
}
