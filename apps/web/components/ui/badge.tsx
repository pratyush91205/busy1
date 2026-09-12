import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

/**
 * Tones. Every badge carries readable text as well as its colour - colour
 * alone is not a label, and roughly one in twelve men cannot tell the amber
 * from the green.
 *
 * The five maintenance tones come from the tokens in globals.css, so a status
 * looks the same in a badge, a row accent and the lifecycle rail.
 */
const TONES = {
  neutral: "border-border bg-muted text-muted-foreground",
  due: "border-due/25 bg-due-soft text-due",
  overdue: "border-overdue/30 bg-overdue-soft text-overdue",
  booked: "border-booked/25 bg-booked-soft text-booked",
  in_service: "border-in-service/25 bg-in-service-soft text-in-service",
  completed: "border-completed/25 bg-completed-soft text-completed",
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
        "inline-flex items-center rounded border px-1.5 py-0.5 text-[11px] font-medium tracking-wide whitespace-nowrap uppercase",
        TONES[tone],
        className,
      )}
      {...props}
    />
  );
}

export { Badge };
