/**
 * Where the access token lives.
 *
 * localStorage, sent as a bearer header, rather than an httpOnly cookie. The
 * API and the frontend are on different origins, so a cookie would need
 * SameSite=None, Secure and credentialed CORS on both ends - more moving parts
 * to get wrong than the XSS exposure it removes, on a project with no
 * user-generated HTML. See docs/decisions.md.
 *
 * Nothing here is a security boundary. The token is what the server checks;
 * clearing it only ends the session in this browser.
 */

const TOKEN_KEY = "fleet.access_token";

/** Fires when the token is set or cleared, so open queries can react. */
const TOKEN_CHANGED = "fleet:token-changed";

export function readToken(): string | null {
  // Server-rendered passes and private-mode browsers both have to survive this.
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function storeToken(token: string): void {
  try {
    window.localStorage.setItem(TOKEN_KEY, token);
  } catch {
    // Storage disabled. The session lasts as long as the page does; the app
    // still works, so this is not worth failing the login over.
  }
  announce();
}

export function clearToken(): void {
  try {
    window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    // Nothing to clear.
  }
  announce();
}

export function onTokenChange(listener: () => void): () => void {
  window.addEventListener(TOKEN_CHANGED, listener);
  // "storage" only fires in *other* tabs, which is exactly what makes logging
  // out in one tab log out the rest.
  window.addEventListener("storage", listener);
  return () => {
    window.removeEventListener(TOKEN_CHANGED, listener);
    window.removeEventListener("storage", listener);
  };
}

function announce(): void {
  window.dispatchEvent(new Event(TOKEN_CHANGED));
}
