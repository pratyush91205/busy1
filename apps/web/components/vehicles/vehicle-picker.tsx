"use client";

import { useEffect, useId, useRef, useState } from "react";

import { Input } from "@/components/ui/input";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { useVehicle, useVehicles } from "@/hooks/use-vehicles";
import { cn } from "@/lib/utils";

/**
 * Pick one vehicle, searching the server.
 *
 * The alternative - fetch the first hundred vehicles and filter them in the
 * browser - is the thing this project is not allowed to do, and it silently
 * stops working at vehicle 101. This asks the API for ten matches at a time
 * using the same `search` parameter the fleet list uses.
 *
 * Built on an input and a listbox rather than a native select because the
 * options arrive asynchronously; the keyboard contract is implemented by hand
 * to match what a select would have given for free.
 */
export function VehiclePicker({
  value,
  onChange,
  includeArchived = false,
  placeholder = "All vehicles",
  id,
  className,
}: {
  value?: number;
  onChange: (vehicleId: number | undefined) => void;
  includeArchived?: boolean;
  placeholder?: string;
  id?: string;
  className?: string;
}) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const listId = `${inputId}-list`;

  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [highlighted, setHighlighted] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const search = useDebouncedValue(query, 250);
  const { data, isFetching } = useVehicles(
    { search, limit: 10, include_archived: includeArchived },
    open,
  );
  // So a vehicle chosen by id in the URL shows its registration, not its id.
  const selected = useVehicle(value ?? 0, value !== undefined);

  const options = data?.items ?? [];

  // Clicking anywhere else closes it, which is what a select does.
  useEffect(() => {
    if (!open) return;

    function onPointerDown(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    }

    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, [open]);

  function choose(vehicleId: number | undefined) {
    onChange(vehicleId);
    setOpen(false);
    setQuery("");
  }

  const label = selected.data
    ? `${selected.data.registration_number} — ${selected.data.make} ${selected.data.model}`
    : value !== undefined
      ? "…"
      : "";

  return (
    <div ref={containerRef} className={cn("relative", className)}>
      <Input
        id={inputId}
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        autoComplete="off"
        placeholder={value !== undefined ? label : placeholder}
        value={open ? query : value !== undefined ? label : ""}
        onChange={(event) => {
          setQuery(event.target.value);
          setHighlighted(0);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown") {
            event.preventDefault();
            setOpen(true);
            setHighlighted((index) => Math.min(index + 1, options.length - 1));
          } else if (event.key === "ArrowUp") {
            event.preventDefault();
            setHighlighted((index) => Math.max(index - 1, 0));
          } else if (event.key === "Enter" && open) {
            event.preventDefault();
            const option = options[highlighted];
            if (option) choose(option.id);
          } else if (event.key === "Escape") {
            setOpen(false);
            setQuery("");
          } else if (event.key === "Backspace" && query === "" && value !== undefined) {
            choose(undefined);
          }
        }}
        className={cn(value !== undefined && !open && "font-medium")}
      />

      {value !== undefined && !open ? (
        <button
          type="button"
          onClick={() => choose(undefined)}
          aria-label="Clear the vehicle filter"
          className="text-muted-foreground hover:text-foreground absolute top-1/2 right-1.5 -translate-y-1/2 rounded px-1 text-sm leading-none"
        >
          &times;
        </button>
      ) : null}

      {open ? (
        <ul
          id={listId}
          role="listbox"
          aria-label="Vehicles"
          className="bg-popover absolute z-30 mt-1 max-h-64 w-full min-w-64 overflow-auto rounded-md border p-1 shadow-lg"
        >
          {options.length === 0 ? (
            <li className="text-muted-foreground px-2 py-3 text-center text-sm">
              {isFetching ? "Searching…" : "No vehicles match that."}
            </li>
          ) : (
            options.map((vehicle, index) => (
              <li key={vehicle.id}>
                <button
                  type="button"
                  role="option"
                  aria-selected={vehicle.id === value}
                  onMouseEnter={() => setHighlighted(index)}
                  onClick={() => choose(vehicle.id)}
                  className={cn(
                    "flex w-full items-baseline gap-2 rounded px-2 py-1.5 text-left text-sm",
                    index === highlighted && "bg-muted",
                  )}
                >
                  <span className="font-medium">
                    {vehicle.registration_number}
                  </span>
                  <span className="text-muted-foreground truncate text-xs">
                    {vehicle.make} {vehicle.model}
                  </span>
                  {vehicle.is_archived ? (
                    <span className="text-muted-foreground ml-auto text-[11px] uppercase">
                      Archived
                    </span>
                  ) : null}
                </button>
              </li>
            ))
          )}
        </ul>
      ) : null}
    </div>
  );
}
