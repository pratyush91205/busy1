import { Badge, type BadgeTone } from "@/components/ui/badge";
import { STATUS_LABELS, type ServiceStatus } from "@/types/service";

/**
 * One mapping from status to label and tone, used everywhere a status is
 * shown, so two screens cannot disagree about what Booked looks like.
 *
 * Overdue is shown in place of DUE, but it is not a fifth status: the record
 * underneath is still `due`, and every filter, transition and API contract
 * still names one of the four stored values. That is why it arrives here as a
 * flag rather than as another value in the union.
 */
const TONES: Record<ServiceStatus, BadgeTone> = {
  due: "due",
  booked: "booked",
  in_service: "in_service",
  completed: "completed",
};

export function StatusBadge({
  status,
  isOverdue = false,
  className,
}: {
  status: ServiceStatus;
  isOverdue?: boolean;
  className?: string;
}) {
  if (isOverdue) {
    return (
      <Badge tone="overdue" className={className}>
        Overdue
      </Badge>
    );
  }

  return (
    <Badge tone={TONES[status]} className={className}>
      {STATUS_LABELS[status]}
    </Badge>
  );
}

/**
 * The colour a status lends to a row - a 2px rule down the left edge, which
 * reads at a glance in a long table without turning the row into a highlight.
 */
export const STATUS_ACCENT: Record<ServiceStatus, string> = {
  due: "border-l-due",
  booked: "border-l-booked",
  in_service: "border-l-in-service",
  completed: "border-l-completed",
};

export function accentFor(status: ServiceStatus, isOverdue: boolean): string {
  return isOverdue ? "border-l-overdue" : STATUS_ACCENT[status];
}
