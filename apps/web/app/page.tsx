"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useCurrentUser } from "@/hooks/use-auth";
import { landingRouteFor } from "@/lib/routes";

/** Sends the visitor wherever their session says they belong. */
export default function Home() {
  const router = useRouter();
  const { user, isLoading } = useCurrentUser();

  useEffect(() => {
    if (isLoading) return;
    router.replace(user ? landingRouteFor(user) : "/login");
  }, [isLoading, user, router]);

  return (
    <output
      aria-live="polite"
      className="text-muted-foreground flex min-h-full items-center justify-center text-sm"
    >
      Loading&#8230;
    </output>
  );
}
