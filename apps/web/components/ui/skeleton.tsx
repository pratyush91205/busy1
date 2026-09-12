import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

function Skeleton({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="skeleton"
      className={cn("bg-muted animate-pulse rounded", className)}
      {...props}
    />
  );
}

/**
 * A placeholder shaped like the table it stands in for, rather than one grey
 * block - the row height and column count are what stop the page jumping when
 * the data lands.
 */
function TableSkeleton({
  rows = 6,
  columns = 5,
  label,
}: {
  rows?: number;
  columns?: number;
  label: string;
}) {
  return (
    <div className="rounded-md border" aria-busy="true" aria-label={label}>
      <div className="bg-subtle h-9 border-b" />
      {Array.from({ length: rows }, (_, row) => (
        <div
          key={row}
          className="flex items-center gap-4 border-b px-3 py-2.5 last:border-0"
        >
          {Array.from({ length: columns }, (_, column) => (
            <Skeleton
              key={column}
              className="h-4"
              style={{ width: column === 0 ? "7rem" : `${5 + (column % 3) * 3}rem` }}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

export { Skeleton, TableSkeleton };
