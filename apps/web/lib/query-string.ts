/**
 * Query objects to query strings, one way, everywhere.
 *
 * Empty and undefined values are dropped rather than sent: `?search=` matches
 * nothing useful, and it would make two identical views cache under different
 * keys.
 */
export function toSearchParams(query: object): string {
  const params = new URLSearchParams();

  for (const [key, value] of Object.entries(query) as [string, unknown][]) {
    if (value === undefined || value === null || value === "") continue;
    params.set(key, String(value));
  }

  const encoded = params.toString();
  return encoded ? `?${encoded}` : "";
}
