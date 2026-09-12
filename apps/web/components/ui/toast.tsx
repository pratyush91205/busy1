"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { cn } from "@/lib/utils";

/**
 * Confirmation for things that worked.
 *
 * Deliberately narrow: a toast says a mutation succeeded and disappears.
 * Failures are never toasted - they stay inline next to the control that
 * failed, carrying the server's own message, because a message that vanishes
 * after four seconds is no way to report "odometer 4000 is lower than 52300".
 */
type Toast = { id: number; message: string };

const ToastContext = createContext<((message: string) => void) | null>(null);

const LIFETIME = 4000;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const notify = useCallback((message: string) => {
    const id = Date.now() + Math.random();
    setToasts((current) => [...current, { id, message }]);
    setTimeout(
      () => setToasts((current) => current.filter((item) => item.id !== id)),
      LIFETIME,
    );
  }, []);

  const value = useMemo(() => notify, [notify]);

  return (
    <ToastContext.Provider value={value}>
      {children}

      {/* polite, not assertive: a success does not interrupt what someone is
          reading. */}
      <div
        aria-live="polite"
        className="pointer-events-none fixed inset-x-0 top-3 z-50 flex flex-col items-center gap-2 px-4"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={cn(
              "bg-foreground text-background pointer-events-auto rounded-md px-3 py-2 text-sm shadow-lg",
              "[animation:toast-in_120ms_ease-out]",
            )}
          >
            {toast.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

/** Returns a function that shows a short confirmation. */
export function useToast() {
  const notify = useContext(ToastContext);
  if (!notify) {
    throw new Error("useToast must be used inside a ToastProvider");
  }
  return notify;
}
