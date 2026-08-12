import type { SeasonStageStatus } from "@/entities";
import { StatusBadge } from "@/shared/ui/StatusBadge";

type StageStatusPillProps = {
  status: SeasonStageStatus;
};

const statusLabel: Record<SeasonStageStatus, string> = {
  completed: "Завершен",
  available: "Активный",
  locked: "Закрыт"
};

const statusVariant = {
  completed: "completed",
  available: "live",
  locked: "scheduled"
} as const;

export function StageStatusPill({ status }: StageStatusPillProps) {
  return <StatusBadge variant={statusVariant[status]}>{statusLabel[status]}</StatusBadge>;
}
