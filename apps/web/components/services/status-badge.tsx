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
  due: "warning",
  booked: "info",
  in_service: "active",
  completed: "success",
};

export function StatusBadge({
  status,
  isOverdue = false,
}: {
  status: ServiceStatus;
  isOverdue?: boolean;
}) {
  if (isOverdue) {
    return <Badge tone="danger">OVERDUE</Badge>;
  }
  return <Badge tone={TONES[status]}>{STATUS_LABELS[status]}</Badge>;
}
