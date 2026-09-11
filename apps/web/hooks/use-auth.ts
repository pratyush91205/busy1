"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useSyncExternalStore } from "react";

import { apiFetch, ApiError } from "@/lib/api-client";
import { clearToken, onTokenChange, readToken, storeToken } from "@/lib/auth";
import type { LoginResponse, User } from "@/types/auth";

export const CURRENT_USER_KEY = ["auth", "me"] as const;

const neverChanges = () => () => {};
const onServer = () => false;
const onClient = () => true;
const noTokenOnServer = () => null;

/**
 * Whether a token is present in this browser.
 *
 * localStorage is an external store, not React state, so it is subscribed to
 * rather than copied into state in an effect - which would re-render every
 * consumer twice on mount.
 *
 * The token is null during the server render and the hydration that matches
 * it, so `ready` says which side we are on. Without it the shell cannot tell
 * "nobody is signed in" from "we have not looked yet", and flashes the login
 * page at someone who is signed in.
 */
export function useToken() {
  const token = useSyncExternalStore(onTokenChange, readToken, noTokenOnServer);
  const ready = useSyncExternalStore(neverChanges, onClient, onServer);

  return { token: ready ? token : null, ready };
}

/**
 * The signed-in user, from the server.
 *
 * The user is never read out of the token. The token says who the client
 * claims to be; /auth/me is the server saying who it actually is, which is
 * also what makes a stale or tampered token show up as signed-out rather than
 * as a fake session.
 */
export function useCurrentUser() {
  const { token, ready } = useToken();

  const query = useQuery<User, ApiError>({
    queryKey: CURRENT_USER_KEY,
    queryFn: () => apiFetch<User>("/auth/me"),
    enabled: ready && token !== null,
    // A rejected token will be rejected again; retrying only delays the
    // redirect to /login.
    retry: false,
    staleTime: 5 * 60_000,
  });

  return {
    user: token === null ? null : (query.data ?? null),
    // "Still deciding" - distinct from "decided, and nobody is signed in".
    isLoading: !ready || (token !== null && query.isPending),
    error: query.error,
  };
}

export function useLogin() {
  const queryClient = useQueryClient();

  return useMutation<LoginResponse, ApiError, { email: string; password: string }>({
    mutationFn: (credentials) =>
      apiFetch<LoginResponse>("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(credentials),
      }),
    onSuccess: (data) => {
      storeToken(data.access_token);
      // Seed the cache from the login response so the shell renders without a
      // second round trip.
      queryClient.setQueryData(CURRENT_USER_KEY, data.user);
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();

  return useCallback(() => {
    clearToken();
    // Not just the user: every cached answer was fetched as that user, and
    // leaving it behind would show one account's data to the next.
    queryClient.clear();
  }, [queryClient]);
}
