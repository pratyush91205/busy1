import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

/**
 * A styled native `<select>`.
 *
 * Native rather than a headless listbox: keyboard behaviour, type-ahead and
 * the mobile picker all come for free, and none of it is a dependency to keep
 * current. The filters in this app are short lists of known values, which is
 * exactly what a native select is good at.
 */
function Select({ className, ...props }: ComponentProps<"select">) {
  return (
    <select
      data-slot="select"
      className={cn(
        "border-input bg-background h-8 rounded-md border px-2 pr-7 text-sm",
        "appearance-none bg-[length:14px] bg-[right_0.4rem_center] bg-no-repeat",
        "transition-colors duration-120 hover:bg-muted/60",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      style={{
        backgroundImage:
          // Inline so the arrow inherits nothing and loads nothing.
          "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16' fill='none' stroke='%23888' stroke-width='1.5'><path d='M4 6l4 4 4-4'/></svg>\")",
      }}
      {...props}
    />
  );
}

export { Select };
