import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

const VARIANTS = {
  /** The one action a screen is actually for. */
  default: "bg-primary text-primary-foreground hover:bg-primary/90",
  /** Everything else that is still a real action. */
  outline: "border bg-background hover:bg-muted text-foreground",
  ghost: "hover:bg-muted text-muted-foreground hover:text-foreground",
  danger:
    "border border-overdue/30 bg-overdue-soft text-overdue hover:bg-overdue/15",
} as const;

const SIZES = {
  sm: "h-7 gap-1.5 px-2 text-xs",
  md: "h-9 gap-2 px-3.5",
  icon: "size-9",
} as const;

type ButtonProps = ComponentProps<"button"> & {
  variant?: keyof typeof VARIANTS;
  size?: keyof typeof SIZES;
};

function Button({
  className,
  variant = "default",
  size = "md",
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      // Defaulting to "button": a bare <button> inside a form submits it, and
      // every accidental submit in this app is a mutation.
      type={type}
      data-slot="button"
      className={cn(
        "inline-flex items-center justify-center rounded-md text-sm font-medium whitespace-nowrap",
        "transition-colors duration-120",
        "disabled:pointer-events-none disabled:opacity-50",
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
      {...props}
    />
  );
}

export { Button };
