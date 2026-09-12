"use client";

import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/** The toolbar above a list. Controls left, actions right. */
export function FilterBar({
  children,
  actions,
  className,
}: {
  children: ReactNode;
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-2 rounded-md border px-2.5 py-2",
        className,
      )}
    >
      <div className="flex flex-1 flex-wrap items-center gap-2">{children}</div>
      {actions ? (
        <div className="flex items-center gap-2">{actions}</div>
      ) : null}
    </div>
  );
}

/**
 * One filter that is currently narrowing the list, with the way to undo it.
 *
 * Worth the space: a manager who has navigated in from a dashboard link needs
 * to see *why* they are looking at eleven records rather than four hundred.
 */
export function FilterChip({
  label,
  value,
  onClear,
}: {
  label: string;
  value: string;
  onClear: () => void;
}) {
  return (
    <span className="bg-muted text-muted-foreground inline-flex items-center gap-1.5 rounded px-2 py-1 text-xs">
      <span className="text-foreground/70">{label}:</span>
      <span className="text-foreground font-medium">{value}</span>
      <button
        type="button"
        onClick={onClear}
        className="hover:text-foreground -mr-0.5 ml-0.5 rounded px-1 leading-none transition-colors duration-120"
        aria-label={`Clear ${label} filter`}
      >
        &times;
      </button>
    </span>
  );
}
