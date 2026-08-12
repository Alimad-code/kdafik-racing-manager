import type { CSSProperties } from "react";
import type { RaceResult, StageWeather, Team, Track } from "@/entities";
import { formatDriverName, getTeam } from "@/features/season/lib/seasonViewData";
import { formatPositionLabel } from "@/shared/lib/positionLabel";
import { getReadableTeamAccent } from "@/shared/lib/teamAccent";
import { cn } from "@/shared/lib/utils";
import { TeamIcon } from "@/shared/ui";
import { RaceWeatherForecast } from "@/pages/_shared/race-weekend/RaceWeatherForecast";
import type { GridRow } from "@/pages/_shared/race-weekend/types";
import { FALLBACK_TEAM_COLOR, getTeamAccent } from "@/pages/_shared/race-weekend/raceWeekendUtils";

function RacePerformanceSummary({ rows }: { rows: RaceResult[] }) {
  const byFinish = (left: RaceResult, right: RaceResult) => left.position - right.position;
  const lapMilliseconds = (lap: string) => {
    const match = /^(\d+):(\d{2})\.(\d{3})$/.exec(lap);
    return match
      ? Number(match[1]) * 60_000 + Number(match[2]) * 1_000 + Number(match[3])
      : Infinity;
  };
  const fastest = rows
    .filter((row) => row.bestLap && row.bestLapNumber)
    .sort(
      (left, right) =>
        lapMilliseconds(left.bestLap!) - lapMilliseconds(right.bestLap!) || byFinish(left, right)
    )[0];
  const topSpeed = rows
    .filter((row) => row.maxSpeedKph !== undefined)
    .sort((left, right) => right.maxSpeedKph! - left.maxSpeedKph! || byFinish(left, right))[0];

  return (
    <section
      className="grid grid-cols-1 gap-px border border-line bg-line"
      aria-label="Рекорды гонки"
    >
      <div className="min-w-0 bg-surface px-4 py-3">
        <p className="metadata-label">Быстрейший круг</p>
        {fastest ? (
          <p className="mt-1 truncate font-mono text-sm font-black uppercase text-foreground">
            {formatDriverName(fastest.driverId)} · {fastest.bestLap} · К
            {fastest.bestLapNumber ?? "-"}
          </p>
        ) : (
          <p className="mt-1 font-mono text-sm font-black uppercase text-muted-foreground">
            Нет данных
          </p>
        )}
      </div>
      <div className="min-w-0 bg-surface px-4 py-3">
        <p className="metadata-label">Максимальная скорость</p>
        {topSpeed ? (
          <p className="mt-1 truncate font-mono text-sm font-black uppercase text-foreground">
            {formatDriverName(topSpeed.driverId)} · {topSpeed.maxSpeedKph!.toFixed(1)} км/ч
          </p>
        ) : (
          <p className="mt-1 font-mono text-sm font-black uppercase text-muted-foreground">
            Нет данных
          </p>
        )}
      </div>
    </section>
  );
}

export function RaceContextPanel({
  track,
  selectedTeam,
  selectedDriverIds,
  isResultsView,
  gridRows,
  raceResults,
  weather
}: {
  track: Track;
  selectedTeam: Team;
  selectedDriverIds: string[];
  isResultsView: boolean;
  gridRows: GridRow[];
  raceResults: RaceResult[];
  weather?: StageWeather | null;
}) {
  const selectedGridRows = gridRows.filter((row) => selectedDriverIds.includes(row.driverId));
  const winner = raceResults.find((row) => row.position === 1);
  const selectedTeamPoints = raceResults
    .filter((row) => row.teamId === selectedTeam.id)
    .reduce((total, row) => total + row.points, 0);
  const selectedTeamAccent = getReadableTeamAccent(selectedTeam.color || FALLBACK_TEAM_COLOR);
  return (
    <aside
      className={cn(
        "race-event-info-unified font-mono uppercase",
        isResultsView && "race-event-info-unified-right"
      )}
    >
      <div className="flex flex-col gap-1.5 border border-line bg-secondary px-4 py-3.5 font-mono uppercase">
        <span className="text-[10px] font-black tracking-[0.22em] text-muted-foreground">
          ТРАССА
        </span>
        <strong className="text-sm font-black leading-none text-foreground">{track.name}</strong>
      </div>

      <RaceWeatherForecast track={track} weather={weather} finishOnly={isResultsView} />

      {isResultsView ? <RacePerformanceSummary rows={raceResults} /> : null}

      <div
        className="flex flex-col gap-1.5 border border-line bg-secondary px-4 py-3.5 font-mono uppercase"
        data-testid="race-distance-card"
      >
        <span className="text-[10px] font-black tracking-[0.22em] text-muted-foreground">
          Дистанция гонки
        </span>
        <strong className="text-sm font-black leading-none text-foreground">
          {track.laps} кругов
        </strong>
      </div>

      {!isResultsView &&
        selectedGridRows.map((row) => (
          <div
            key={row.id}
            className="race-player-car flex h-[60px] items-center justify-between gap-3"
            style={{ "--team-accent": getTeamAccent(row.teamId) } as CSSProperties}
          >
            <strong className="text-sm font-black leading-none text-foreground">
              {formatDriverName(row.driverId)}
            </strong>
            <b>{formatPositionLabel(row.position)}</b>
          </div>
        ))}

      {isResultsView && winner ? (
        <div
          className="flex flex-col gap-2 border px-4 py-4 font-mono uppercase"
          style={
            {
              "--team-accent": getTeamAccent(winner.teamId),
              background: "color-mix(in srgb, var(--team-accent) 25%, transparent)",
              borderColor: "var(--team-accent)"
            } as CSSProperties
          }
        >
          <span className="text-[10px] font-black tracking-[0.22em] text-foreground">
            Победитель этапа
          </span>
          <strong className="text-xl font-black leading-none text-foreground">
            {formatDriverName(winner.driverId)}
          </strong>
          <div className="flex items-center gap-2 text-[11px] font-black tracking-widest text-foreground/80">
            <TeamIcon
              className="size-4"
              color={getTeam(winner.teamId).color}
              teamId={winner.teamId}
            />
            <span>{getTeam(winner.teamId).name}</span>
          </div>
        </div>
      ) : null}

      {isResultsView ? (
        <div
          className="flex min-h-[60px] items-center justify-between gap-3 border px-4 py-4 font-mono uppercase"
          style={
            {
              "--team-accent": selectedTeamAccent,
              background: "color-mix(in srgb, var(--team-accent) 25%, transparent)",
              borderColor: "var(--team-accent)"
            } as CSSProperties
          }
        >
          <div>
            <span className="text-[10px] font-black tracking-[0.22em] text-foreground">
              Заработано очков
            </span>
            <div className="mt-2 flex items-center gap-2">
              <TeamIcon className="size-4" color={selectedTeam.color} teamId={selectedTeam.id} />
              <strong className="text-sm font-black leading-none text-foreground">
                {selectedTeam.name}
              </strong>
            </div>
          </div>
          <b
            className="border px-3 py-2 text-[15px] font-black tracking-[0.1em]"
            style={{
              background: "color-mix(in srgb, var(--team-accent) 30%, transparent)",
              borderColor: "var(--team-accent)",
              color: "var(--team-accent)"
            }}
          >
            +{selectedTeamPoints}
          </b>
        </div>
      ) : null}
    </aside>
  );
}
