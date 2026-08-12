import type { Team } from "@/entities";
import { MetricRow } from "@/shared/ui/MetricRow";
import { StatusBadge } from "@/shared/ui/StatusBadge";
import { TeamIcon } from "@/shared/ui/TeamIcon";

type TeamSummaryProps = {
  team: Team;
  selected?: boolean;
  slotCode?: string;
};

export function TeamSummary({ team, selected = false, slotCode }: TeamSummaryProps) {
  return (
    <article className="race-panel border-l-2 border-l-primary/70 p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            {slotCode ? (
              <span className="timing-value text-sm text-primary">{slotCode}</span>
            ) : null}
            <p className="metadata-label">{team.baseCountry}</p>
          </div>
          <div className="mt-2 flex items-center gap-2">
            <TeamIcon className="size-5" color={team.color} teamId={team.id} />
            <h3 className="text-xl font-black uppercase text-foreground">{team.name}</h3>
          </div>
          <p className="mt-1 font-mono text-sm font-bold text-muted-foreground">{team.powerUnit}</p>
        </div>
        <StatusBadge variant={selected ? "live" : "neutral"}>
          {selected ? "Выбрана" : "Доступна"}
        </StatusBadge>
      </div>
      <div className="mt-5 border-t border-border pt-2">
        <MetricRow label="Рейтинг болида" value={team.carRating} detail="Общий потенциал болида" />
        <MetricRow label="Надежность" value={team.reliability} detail="Риск техпроблем" />
        <MetricRow
          label="Настройка"
          value={`$${team.setupCost.toFixed(1)}M`}
          detail="Цена настройки"
        />
      </div>
    </article>
  );
}
