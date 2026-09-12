import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";

/**
 * The two states a list spends most of its life in when something is wrong,
 * written once so every screen says them the same way.
 */
export function EmptyState({
  title,
  hint,
  action,
}: {
  title: string;
  /** What would put something here - not "no data". */
  hint?: string;
  action?: ReactNode;
}) {
  return (
    <div className="rounded-md border border-dashed px-6 py-12 text-center">
      <p className="text-sm font-medium">{title}</p>
      {hint ? (
        <p className="text-muted-foreground mx-auto mt-1 max-w-sm text-sm">
          {hint}
        </p>
      ) : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

export function ErrorState({
  title = "Could not load this",
  message,
  onRetry,
}: {
  title?: string;
  /** The server's own words. Never replaced with something friendlier. */
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div
      role="alert"
      className="border-overdue/30 bg-overdue-soft rounded-md border px-4 py-3"
    >
      <p className="text-overdue text-sm font-medium">{title}</p>
      <p className="text-overdue/90 mt-0.5 text-sm">{message}</p>
      {onRetry ? (
        <Button variant="outline" size="sm" className="mt-3" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </div>
  );
}
