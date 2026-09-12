"use client";

import { useEffect, useRef, type ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * A dialog built on the native `<dialog>` element rather than a headless UI
 * library. `showModal()` already gives focus trapping, Escape to close, inert
 * background and the top layer - which is most of what the library would be
 * for, and none of it is another dependency to keep current.
 */
export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  className,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: ReactNode;
  className?: string;
}) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;

    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      // Escape and the backdrop both close it; "cancel" is the event the
      // native element fires for Escape.
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        if (event.target === ref.current) onClose();
      }}
      className={cn(
        "bg-background text-foreground m-auto w-[calc(100vw-2rem)] max-w-md rounded-lg border p-0 shadow-xl",
        "backdrop:bg-black/50",
        className,
      )}
      aria-labelledby="modal-title"
    >
      <div className="space-y-4 p-4">
        <header className="space-y-1">
          <h2 id="modal-title" className="text-sm font-semibold">
            {title}
          </h2>
          {description ? (
            <p className="text-muted-foreground text-sm leading-relaxed">
              {description}
            </p>
          ) : null}
        </header>

        {children}
      </div>
    </dialog>
  );
}
