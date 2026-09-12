"use client";

import { TableHead } from "@/components/ui/table";
import { cn } from "@/lib/utils";

/**
 * A sortable column header.
 *
 * Sorting is the server's: this writes a query parameter and the next page
 * comes back ordered. `aria-sort` goes on the cell rather than the button,
 * which is where a screen reader looks for it.
 */
export function SortableHead<T extends string>({
  label,
  column,
  active,
  order,
  onSort,
  className,
}: {
  label: string;
  column: T;
  active: T;
  order: "asc" | "desc";
  onSort: (column: T) => void;
  className?: string;
}) {
  const isActive = active === column;

  return (
    <TableHead
      aria-sort={
        isActive ? (order === "asc" ? "ascending" : "descending") : "none"
      }
      className={cn("p-0", className)}
    >
      <button
        type="button"
        onClick={() => onSort(column)}
        className={cn(
          "hover:text-foreground flex h-8 w-full items-center gap-1 px-3 transition-colors duration-120",
          isActive && "text-foreground font-semibold",
        )}
      >
        {label}
        <span
          aria-hidden
          className={cn("text-[10px]", isActive ? "opacity-100" : "opacity-0")}
        >
          {order === "asc" ? "▲" : "▼"}
        </span>
      </button>
    </TableHead>
  );
}
