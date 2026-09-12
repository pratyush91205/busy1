"use client";

import { useEffect, useState } from "react";

/**
 * The value, a beat after it stops changing.
 *
 * Search boxes in this app write to the URL and re-request from the server, so
 * without this a ten-character registration is ten history entries and ten
 * round trips. The input itself stays uncontrolled-fast; only the query waits.
 */
export function useDebouncedValue<T>(value: T, delay = 300): T {
  const [settled, setSettled] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setSettled(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return settled;
}
