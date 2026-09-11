import { Badge, type BadgeTone } from "@/components/ui/badge";
import { STATUS_LABELS, type ServiceStatus } from "@/types/service";

/**
 * One mapping from status to label and tone, used everywhere a status is
 * shown, so two screens cannot disagree about what Booked looks like.
 *
 * Overdue is added here in the next spec. It is not a fifth status - it is
 * `due` plus an elapsed grace period - so it will arrive as a flag on this
 * component rather than a new value in the union.
 */
const TONES: Record<ServiceStatus, BadgeTone> = {
  due: "warning",
  booked: "info",
  in_service: "active",
  completed: "success",
};

export function StatusBadge({ status }: { status: ServiceStatus }) {
  return <Badge tone={TONES[status]}>{STATUS_LABELS[status]}</Badge>;
}
