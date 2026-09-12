import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

function Input({ className, ...props }: ComponentProps<"input">) {
  return (
    <input
      data-slot="input"
      className={cn(
        "border-input bg-background flex h-8 w-full rounded-md border px-2.5 text-sm",
        "transition-colors duration-120",
        "placeholder:text-muted-foreground/70",
        // The global focus ring sits 2px off; on a bordered field that reads
        // as a halo, so inputs take the ring directly on the border.
        "focus-visible:ring-ring focus-visible:ring-2 focus-visible:ring-offset-0",
        "disabled:cursor-not-allowed disabled:opacity-50",
        // Driven by aria-invalid so the error styling and the message the
        // screen reader announces cannot drift apart.
        "aria-invalid:border-destructive aria-invalid:focus-visible:ring-destructive",
        className,
      )}
      {...props}
    />
  );
}

function Textarea({ className, ...props }: ComponentProps<"textarea">) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        "border-input bg-background w-full rounded-md border px-2.5 py-1.5 text-sm",
        "transition-colors duration-120",
        "placeholder:text-muted-foreground/70",
        "focus-visible:ring-ring focus-visible:ring-2 focus-visible:ring-offset-0",
        "disabled:cursor-not-allowed disabled:opacity-50",
        "aria-invalid:border-destructive aria-invalid:focus-visible:ring-destructive",
        className,
      )}
      {...props}
    />
  );
}

export { Input, Textarea };
