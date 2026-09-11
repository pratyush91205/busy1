import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

/**
 * Status tones. Every badge carries readable text as well as its colour -
 * colour alone is not a label, and roughly one in twelve men cannot tell the
 * amber from the green.
 */
const TONES = {
  neutral: "bg-muted text-muted-foreground border-transparent",
  info: "border-sky-600/30 bg-sky-500/10 text-sky-700 dark:text-sky-300",
  active: "border-violet-600/30 bg-violet-500/10 text-violet-700 dark:text-violet-300",
  success: "border-emerald-600/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
  warning: "border-amber-600/30 bg-amber-500/10 text-amber-800 dark:text-amber-300",
  danger: "border-red-600/30 bg-red-500/10 text-red-700 dark:text-red-300",
} as const;

export type BadgeTone = keyof typeof TONES;

function Badge({
  className,
  tone = "neutral",
  ...props
}: ComponentProps<"span"> & { tone?: BadgeTone }) {
  return (
    <span
      data-slot="badge"
      className={cn(
        "inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium whitespace-nowrap",
        TONES[tone],
        className,
      )}
      {...props}
    />
  );
}

export { Badge };
