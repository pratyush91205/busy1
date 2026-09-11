import { cn } from "@/lib/utils";
import { LIFECYCLE, STATUS_LABELS, type ServiceStatus } from "@/types/service";

/**
 * The lifecycle as four steps with the current one marked.
 *
 * Reading order is the transition order, which is the point: a technician
 * should be able to see at a glance that Completed does not follow Due.
 */
export function LifecycleSteps({ status }: { status: ServiceStatus }) {
  const current = LIFECYCLE.indexOf(status);

  return (
    <ol className="flex flex-wrap items-center gap-1 text-xs">
      {LIFECYCLE.map((step, index) => {
        const done = index < current;
        const here = index === current;

        return (
          <li key={step} className="flex items-center gap-1">
            <span
              aria-current={here ? "step" : undefined}
              className={cn(
                "rounded border px-2 py-1 font-medium",
                here && "border-foreground bg-foreground text-background",
                done && "text-muted-foreground border-transparent",
                !here && !done && "text-muted-foreground/60 border-dashed",
              )}
            >
              {STATUS_LABELS[step]}
            </span>
            {index < LIFECYCLE.length - 1 ? (
              <span aria-hidden className="text-muted-foreground/50">
                →
              </span>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}
