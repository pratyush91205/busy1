"use client";

import { useEffect, useState, useSyncExternalStore } from "react";

import { cn } from "@/lib/utils";

/**
 * The sign-in page's illustration: one van going round its service cycle.
 *
 * It explains the rule the product is built on rather than decorating the
 * page - whichever interval runs out first opens a service, the service moves
 * through four steps, and completing it resets both counters. The figures are
 * invented and labelled as such. Nothing is read from the API, because nobody
 * is signed in yet.
 */

const MILEAGE_INTERVAL_KM = 8_000;
const DATE_INTERVAL_DAYS = 120;
const FIRST_ODOMETER_KM = 18_400;

// Full class names, so Tailwind can see them.
const STEPS = [
  { label: "Due", bar: "bg-due", text: "text-due" },
  { label: "Booked", bar: "bg-booked", text: "text-booked" },
  { label: "In service", bar: "bg-in-service", text: "text-in-service" },
  { label: "Completed", bar: "bg-completed", text: "text-completed" },
] as const;

/** A quarter-second tick: six seconds of driving, then two on each step. */
const TICK_MS = 250;
const DRIVE_TICKS = 24;
const STEP_TICKS = 8;
const CYCLE_TICKS = DRIVE_TICKS + STEP_TICKS * STEPS.length;

/** How far the clock gets while the mileage runs out. Mileage is what trips. */
const DAYS_SHARE = 0.7;

// A fixed locale, so the server render and the hydrated one agree.
const figures = new Intl.NumberFormat("en-GB");

const REDUCED_MOTION = "(prefers-reduced-motion: reduce)";

function subscribeToMotionPreference(onChange: () => void) {
  const query = window.matchMedia(REDUCED_MOTION);
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
}

const prefersReducedMotion = () => window.matchMedia(REDUCED_MOTION).matches;
const motionAllowedOnServer = () => false;

type Frame = {
  cycle: number;
  /** Index into STEPS, or -1 while the van is still driving. */
  step: number;
  odometerKm: number;
  sinceServiceKm: number;
  sinceServiceDays: number;
};

function frameAt(tick: number): Frame {
  const cycle = Math.floor(tick / CYCLE_TICKS);
  const t = tick % CYCLE_TICKS;
  const driven = Math.min(t / DRIVE_TICKS, 1);
  const drivenKm = Math.round((driven * MILEAGE_INTERVAL_KM) / 50) * 50;
  const step =
    t < DRIVE_TICKS ? -1 : Math.floor((t - DRIVE_TICKS) / STEP_TICKS);

  // Completing the service is what resets both counters. The odometer itself
  // never goes back: the next cycle counts on from where this one finished.
  const completed = step === STEPS.length - 1;

  return {
    cycle: cycle + 1,
    step,
    odometerKm: FIRST_ODOMETER_KM + cycle * MILEAGE_INTERVAL_KM + drivenKm,
    sinceServiceKm: completed ? 0 : drivenKm,
    sinceServiceDays: completed
      ? 0
      : Math.round(driven * DATE_INTERVAL_DAYS * DAYS_SHARE),
  };
}

export function ServiceCyclePreview() {
  const reducedMotion = useSyncExternalStore(
    subscribeToMotionPreference,
    prefersReducedMotion,
    motionAllowedOnServer,
  );
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (reducedMotion) return;
    const id = window.setInterval(() => setTick((t) => t + 1), TICK_MS);
    return () => window.clearInterval(id);
  }, [reducedMotion]);

  // Held still, it shows the moment that matters: the interval reached and
  // the service Due.
  const frame = frameAt(reducedMotion ? DRIVE_TICKS : tick);
  const mileageReached = frame.sinceServiceKm >= MILEAGE_INTERVAL_KM;

  return (
    // `dark` swaps in the dark palette for this panel only, status colours
    // included, so it needs no colours of its own.
    <div className="dark bg-background text-foreground flex h-full flex-col justify-between gap-10 rounded-xl p-10 xl:p-14">
      <div className="max-w-md space-y-3">
        <h2 className="text-2xl font-semibold tracking-tight text-balance">
          Every vehicle runs on two counters.
        </h2>
        <p className="text-muted-foreground text-base leading-relaxed">
          A service opens when the mileage or the time since the last one runs
          out, whichever comes first. Completing it resets both.
        </p>
      </div>

      <div
        aria-hidden
        className="bg-card w-full max-w-lg space-y-7 rounded-lg border p-6"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="font-semibold">VAN004</p>
            <p className="text-muted-foreground text-xs">Vauxhall Vivaro</p>
          </div>
          <p className="text-muted-foreground text-xs tabular-nums">
            Service cycle {frame.cycle}
          </p>
        </div>

        <div className="space-y-1">
          <p className="text-muted-foreground text-xs">Odometer</p>
          <p className="text-5xl font-semibold tracking-tight tabular-nums">
            {figures.format(frame.odometerKm)}
            <span className="text-muted-foreground ml-2 text-lg font-normal">
              km
            </span>
          </p>
        </div>

        <div className="space-y-4">
          <Meter
            label={mileageReached ? "Mileage interval reached" : "Mileage"}
            detail={`${figures.format(frame.sinceServiceKm)} of ${figures.format(MILEAGE_INTERVAL_KM)} km`}
            share={frame.sinceServiceKm / MILEAGE_INTERVAL_KM}
            reached={mileageReached}
          />
          <Meter
            label="Time"
            detail={`${frame.sinceServiceDays} of ${DATE_INTERVAL_DAYS} days`}
            share={frame.sinceServiceDays / DATE_INTERVAL_DAYS}
            reached={false}
          />
        </div>

        <ol className="grid grid-cols-4 gap-2">
          {STEPS.map((step, index) => {
            const current = index === frame.step;
            const done = index < frame.step;
            return (
              <li key={step.label} className="space-y-2">
                <span
                  className={cn(
                    "block h-1 rounded-full transition-colors duration-300",
                    current ? step.bar : done ? "bg-foreground/40" : "bg-foreground/10",
                  )}
                />
                <span
                  className={cn(
                    "block text-xs transition-colors duration-300",
                    current
                      ? cn(step.text, "font-medium")
                      : done
                        ? "text-foreground/70"
                        : "text-muted-foreground",
                  )}
                >
                  {step.label}
                </span>
              </li>
            );
          })}
        </ol>
      </div>

      <p className="text-muted-foreground text-xs">
        Illustration with sample figures.
      </p>
    </div>
  );
}

function Meter({
  label,
  detail,
  share,
  reached,
}: {
  label: string;
  detail: string;
  share: number;
  reached: boolean;
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between gap-4 text-xs">
        <span className={reached ? "text-due font-medium" : "text-muted-foreground"}>
          {label}
        </span>
        <span className="text-foreground/80 tabular-nums">{detail}</span>
      </div>
      <div className="bg-foreground/10 h-1.5 overflow-hidden rounded-full">
        <div
          className={cn(
            "h-full rounded-full transition-[width,background-color] duration-250 ease-linear",
            reached ? "bg-due" : "bg-foreground/60",
          )}
          style={{ width: `${Math.min(share, 1) * 100}%` }}
        />
      </div>
    </div>
  );
}
