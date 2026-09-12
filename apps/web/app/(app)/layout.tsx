"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { ManagerShell } from "@/components/shell/manager-shell";
import { TechnicianShell } from "@/components/shell/technician-shell";
import { useCurrentUser } from "@/hooks/use-auth";

/**
 * The shell every signed-in page renders inside.
 *
 * Which shell depends on the role, because the two jobs are not the same job.
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

  const Shell = user.role === "fleet_manager" ? ManagerShell : TechnicianShell;

  return (
    <>
      <a
        href="#content"
        className="bg-background sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-md focus:border focus:px-3 focus:py-2 focus:text-sm"
      >
        Skip to content
      </a>
      <Shell user={user}>{children}</Shell>
    </>
  );
}
