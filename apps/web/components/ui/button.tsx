import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

type ButtonProps = ComponentProps<"button"> & {
  variant?: "default" | "ghost";
};

function Button({ className, variant = "default", ...props }: ButtonProps) {
  return (
    <button
      data-slot="button"
      className={cn(
        "inline-flex h-9 items-center justify-center gap-2 rounded-md px-4 text-sm font-medium whitespace-nowrap transition-colors",
        "focus-visible:ring-ring focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none",
        "disabled:pointer-events-none disabled:opacity-50",
        variant === "default" &&
          "bg-primary text-primary-foreground hover:bg-primary/90",
        variant === "ghost" && "hover:bg-muted text-foreground",
        className,
      )}
      {...props}
    />
  );
}

export { Button };
