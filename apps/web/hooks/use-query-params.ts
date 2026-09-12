"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";

/**
 * The URL as the list's state.
 *
 * Every filter, sort and page on a list screen lives here rather than in
 * React state, so a filtered view can be linked, reloaded and shared - and so
 * the browser's back button means what it looks like it means.
 */
export function useQueryParams(pathname: string) {
  const router = useRouter();
  const params = useSearchParams();

  const setParams = useCallback(
    (changes: Record<string, string | number | boolean | null | undefined>) => {
      const next = new URLSearchParams(params.toString());

      for (const [key, value] of Object.entries(changes)) {
        if (value === null || value === undefined || value === "" || value === false) {
          next.delete(key);
        } else {
          next.set(key, String(value));
        }
      }

      // Any change to a filter invalidates the page number: page 7 of a
      // narrower result set is usually empty.
      if (!("page" in changes)) next.delete("page");

      const query = next.toString();
      // scroll: false - changing a filter should not throw the reader back to
      // the top of the page they are already reading.
      router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
    },
    [params, pathname, router],
  );

  return { params, setParams };
}
