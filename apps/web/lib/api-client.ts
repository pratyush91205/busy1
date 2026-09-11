/**
 * The single place the browser learns where the API lives.
 *
 * The base URL comes from NEXT_PUBLIC_API_BASE_URL so that a component never
 * hard-codes a host, and failures carry their HTTP status so the UI can tell
 * "nothing there yet" (404) apart from "something is broken" (everything else).
 */

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = "ApiError";
    this.status = status;
  }
}

/** Raised when NEXT_PUBLIC_API_BASE_URL is missing, rather than fetching "undefined/...". */
export class ApiConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiConfigError";
  }
}

export function apiBaseUrl(): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!base) {
    throw new ApiConfigError(
      "NEXT_PUBLIC_API_BASE_URL is not set. Copy apps/web/.env.example to " +
        ".env.local and point it at the API.",
    );
  }
  return base.replace(/\/$/, "");
}

/** The configured base URL, or null when it is not set. For display only. */
export function configuredApiBaseUrl(): string | null {
  try {
    return apiBaseUrl();
  } catch {
    return null;
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${apiBaseUrl()}${path}`;

  let response: Response;
  try {
    response = await fetch(url, {
      ...init,
      headers: { Accept: "application/json", ...init?.headers },
    });
  } catch (cause) {
    // A network-level failure has no status code; 0 says so honestly.
    throw new ApiError(0, `Could not reach the API at ${url}.`, { cause });
  }

  if (!response.ok) {
    throw new ApiError(response.status, await errorMessage(response));
  }

  return (await response.json()) as T;
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") {
      return body.detail;
    }
  } catch {
    // Fall through to the status text below: an unparseable error body is not
    // itself worth surfacing.
  }
  return response.statusText || `Request failed with status ${response.status}.`;
}
