/**
 * The single place the browser learns where the API lives.
 *
 * The base URL comes from NEXT_PUBLIC_API_BASE_URL so that a component never
 * hard-codes a host, and failures carry their HTTP status so the UI can tell
 * "nothing there yet" (404) apart from "something is broken" (everything else).
 *
 * It also attaches the bearer token when there is one. Authorization remains
 * entirely the server's decision; this only carries the claim to it.
 */

import { clearToken, readToken } from "@/lib/auth";

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
  const token = readToken();

  let response: Response;
  try {
    response = await fetch(url, {
      ...init,
      headers: {
        Accept: "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init?.headers,
      },
    });
  } catch (cause) {
    // A network-level failure has no status code; 0 says so honestly.
    throw new ApiError(0, `Could not reach the API at ${url}.`, { cause });
  }

  if (!response.ok) {
    // A 401 on a request that carried a token means the session is over -
    // expired, revoked, or the user deleted. Drop it, and the authenticated
    // shell sends the browser to /login.
    //
    // Only when a token was actually sent: the 401 from POST /auth/login is a
    // wrong password, and must stay a form error rather than a logout.
    if (response.status === 401 && token) {
      clearToken();
    }
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
