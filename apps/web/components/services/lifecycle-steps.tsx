import { cn } from "@/lib/utils";
import { LIFECYCLE, STATUS_LABELS, type ServiceStatus } from "@/types/service";

const DONE_COLOUR: Record<ServiceStatus, string> = {
  due: "bg-due",
  booked: "bg-booked",
  in_service: "bg-in-service",
  completed: "bg-completed",
};

/**
 * The lifecycle as four steps with the current one marked.
 *
 * Reading order is the transition order, which is the point: a technician
 * should be able to see at a glance that Completed does not follow Due.
 */
export function LifecycleSteps({
  status,
  isOverdue = false,
  className,
}: {
  status: ServiceStatus;
  isOverdue?: boolean;
  className?: string;
}) {
  const current = LIFECYCLE.indexOf(status);

  return (
    <ol className={cn("flex items-center gap-1.5", className)}>
      {LIFECYCLE.map((step, index) => {
        const done = index < current;
        const here = index === current;

        return (
          <li key={step} className="flex flex-1 items-center gap-1.5">
            <div className="min-w-0 flex-1">
              <div
                className={cn(
                  "h-1 rounded-full",
                  done && DONE_COLOUR[step],
                  here && (isOverdue ? "bg-overdue" : DONE_COLOUR[step]),
                  !done && !here && "bg-border",
                )}
              />
              <p
                aria-current={here ? "step" : undefined}
                className={cn(
                  "mt-1.5 text-[11px] tracking-wide uppercase",
                  here
                    ? "text-foreground font-semibold"
                    : done
                      ? "text-muted-foreground"
                      : "text-muted-foreground/50",
                )}
              >
                {/* The record underneath is still Due; Overdue is the derived
                    state, shown where Due would be. */}
                {here && isOverdue ? "Overdue" : STATUS_LABELS[step]}
              </p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
