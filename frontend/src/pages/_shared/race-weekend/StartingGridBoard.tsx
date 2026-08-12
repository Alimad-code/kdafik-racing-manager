import type { CSSProperties } from "react";
import { formatDriverName, getTeam } from "@/features/season/lib/seasonViewData";
import { getReadableTeamAccent } from "@/shared/lib/teamAccent";
import { TeamIcon } from "@/shared/ui";
import type { GridRow } from "@/pages/_shared/race-weekend/types";
import {
  compoundShortLabels,
  compoundStyles,
  FALLBACK_TEAM_COLOR
} from "@/pages/_shared/race-weekend/raceWeekendUtils";

function getTeamTag(team: ReturnType<typeof getTeam>) {
  return team.shortName || team.name;
}

function getGridTimeLabel(row: GridRow) {
  if (row.bestLap) return row.bestLap;
  if (row.status === "no-time") return "Без времени";
  if (row.status === "retired") return "Сход";
  return row.gap;
}

function GridSlot({ row, selectedTeamId }: { row: GridRow; selectedTeamId: string | null }) {
  const team = getTeam(row.teamId);
  const isPlayerTeam = row.teamId === selectedTeamId;
  const sideClassName = row.position % 2 === 0 ? "starting-grid-slot-right" : "";

  return (
    <article
      className={`starting-grid-slot ${sideClassName} ${isPlayerTeam ? "starting-grid-slot-player" : ""}`}
      style={
        {
          "--team-accent": getReadableTeamAccent(team.color || FALLBACK_TEAM_COLOR)
        } as CSSProperties
      }
    >
      <div className="flex min-w-0 items-center gap-2">
        <span className="starting-grid-position">{row.position}</span>
        <div className="flex min-w-0 flex-1 items-center gap-1.5">
          <TeamIcon className="size-4 shrink-0" color={team.color} teamId={team.id} />
          <h3 className="truncate text-[13px] font-black uppercase leading-none text-foreground">
            {formatDriverName(row.driverId)}
          </h3>
          <span className="truncate text-[10px] font-bold uppercase text-muted-foreground">
            {getTeamTag(team)}
          </span>
        </div>
        <span className="font-mono text-[11px] font-bold tabular-nums text-muted-foreground">
          {getGridTimeLabel(row)}
        </span>
        {row.compound ? (
          <span className={`starting-grid-compound ${compoundStyles[row.compound]}`}>
            {compoundShortLabels[row.compound]}
          </span>
        ) : null}
      </div>
    </article>
  );
}

export function StartingGridBoard({
  rows,
  selectedTeamId
}: {
  rows: GridRow[];
  selectedTeamId: string | null;
}) {
  return (
    <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden">
      <div className="starting-grid-title">
        <span className="race-event-title">Стартовая решётка</span>
      </div>
      <div className="starting-grid-track">
        {rows.map((row) => (
          <GridSlot key={row.id} row={row} selectedTeamId={selectedTeamId} />
        ))}
      </div>
    </div>
  );
}
