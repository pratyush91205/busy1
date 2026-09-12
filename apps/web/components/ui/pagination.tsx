"use client";

import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import type { Page } from "@/types/vehicle";

const PAGE_SIZES = [20, 50, 100];

/**
 * The pager for a server-paginated list.
 *
 * It reports the range rather than only the page number, because "21-40 of
 * 134" is what tells a manager how much fleet is left to look at. Every
 * control here changes a query parameter; nothing is sliced in the browser.
 */
export function Pagination<T>({
  page,
  onPage,
  onLimit,
  label = "rows",
}: {
  page: Page<T>;
  onPage: (page: number) => void;
  onLimit?: (limit: number) => void;
  label?: string;
}) {
  const first = (page.page - 1) * page.limit + 1;
  const last = Math.min(page.page * page.limit, page.total);

  return (
    <nav
      aria-label="Pagination"
      className="flex flex-wrap items-center justify-between gap-3 text-sm"
    >
      <p className="text-muted-foreground">
        {page.total === 0
          ? `No ${label}`
          : `${first}–${last} of ${page.total} ${label}`}
      </p>

      <div className="flex items-center gap-2">
        {onLimit ? (
          <label className="text-muted-foreground flex items-center gap-1.5 text-xs">
            Per page
            <Select
              value={String(page.limit)}
              onChange={(event) => onLimit(Number(event.target.value))}
              aria-label="Rows per page"
            >
              {PAGE_SIZES.map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </Select>
          </label>
        ) : null}

        <Button
          variant="outline"
          size="sm"
          disabled={page.page <= 1}
          onClick={() => onPage(page.page - 1)}
        >
          Previous
        </Button>
        <span className="text-muted-foreground text-xs tabular-nums">
          {page.page} / {Math.max(page.total_pages, 1)}
        </span>
        <Button
          variant="outline"
          size="sm"
          disabled={page.page >= page.total_pages}
          onClick={() => onPage(page.page + 1)}
        >
          Next
        </Button>
      </div>
    </nav>
  );
}
