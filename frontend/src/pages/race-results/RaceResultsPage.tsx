import { Minus, Triangle } from "lucide-react";
import type { CSSProperties } from "react";
import { useEffect, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import type { RaceResult } from "@/entities";
import { seasonRepository } from "@/features/season/api/seasonDataSource";
import {
  formatDriverName,
  getCurrentStage,
  getTeam,
  getTrack
} from "@/features/season/lib/seasonViewData";
import { useSeasonStore } from "@/features/season/model/useSeasonStore";
import { CarConditionPanel } from "@/features/season/ui/CarConditionPanel";
import { ROUTES } from "@/shared/constants/routes";
import { formatRaceGap } from "@/shared/lib/raceTiming";
import { getReadableTeamAccent } from "@/shared/lib/teamAccent";
import { cn } from "@/shared/lib/utils";
import { Button, InfoChip, PageHeader, PageSurface, TeamIcon, TimingTable } from "@/shared/ui";
import {
  FALLBACK_TEAM_COLOR,
  getCurrentStageMeta,
  getGrandPrixTitle,
  getStageMeta,
  RaceContextPanel
} from "@/pages/_shared/race-weekend";

function getRaceGapLabel(status: string, gap: string) {
  if (status === "disqualified") return "Дисквалифицирован";
  if (status === "retired") return "Сход";
  if (status === "no-time") return "Без времени";
  return formatRaceGap(gap);
}

function DeltaIndicator({ gridPosition, position }: { gridPosition?: number; position: number }) {
  if (!gridPosition) {
    return <Minus className="mx-auto h-3 w-3 text-muted-foreground/50" />;
  }

  const delta = gridPosition - position;

  if (delta > 0) {
    return (
      <span className="race-results-delta race-results-delta-up">
        <Triangle className="h-2.5 w-2.5 fill-current" />
        <span>{delta}</span>
      </span>
    );
  }

  if (delta < 0) {
    return (
      <span className="race-results-delta race-results-delta-down">
        <Triangle className="h-2.5 w-2.5 rotate-180 fill-current" />
        <span>{Math.abs(delta)}</span>
      </span>
    );
  }

  return <span className="race-results-delta-flat" />;
}

function RaceResultsGrid({
  rows,
  selectedTeamId
}: {
  rows: RaceResult[];
  selectedTeamId: string | null;
}) {
  return (
    <div className="race-results-content">
      <TimingTable
        caption="Результаты гонки"
        density="compact"
        rows={rows}
        getRowKey={(row) => row.id}
        getRowClassName={(row) =>
          row.position === 1
            ? "race-results-winner-row"
            : row.status === "retired" || row.status === "disqualified"
              ? "opacity-70"
              : undefined
        }
        getRowStyle={(row) =>
          row.teamId === selectedTeamId
            ? ({
                "--team-accent": getReadableTeamAccent(
                  getTeam(row.teamId).color || FALLBACK_TEAM_COLOR
                )
              } as CSSProperties)
            : undefined
        }
        columns={[
          {
            key: "position",
            header: "Поз",
            headerClassName: "w-14",
            cellClassName: "w-14",
            render: (row) => <span className="race-results-position">{row.position}</span>
          },
          {
            key: "start",
            header: "Старт",
            align: "center",
            headerClassName: "w-16",
            cellClassName: "w-16",
            render: (row) => (
              <DeltaIndicator gridPosition={row.gridPosition} position={row.position} />
            )
          },
          {
            key: "driver",
            header: "Пилот",
            headerClassName: "min-w-[190px]",
            cellClassName: "min-w-[190px]",
            render: (row) => (
              <p className="truncate font-black text-foreground">
                {formatDriverName(row.driverId)}
              </p>
            )
          },
          {
            key: "team-icon",
            header: <span className="sr-only">Эмблема команды</span>,
            headerClassName: "w-9",
            cellClassName: "w-9",
            render: (row) => {
              const team = getTeam(row.teamId);
              return <TeamIcon className="size-4" color={team.color} teamId={team.id} />;
            }
          },
          {
            key: "team",
            header: "Команда",
            headerClassName: "min-w-[180px]",
            cellClassName: "min-w-[180px]",
            render: (row) => {
              const team = getTeam(row.teamId);
              return <span className="truncate font-semibold text-foreground">{team.name}</span>;
            }
          },
          {
            key: "gap",
            header: "Отст.",
            align: "right",
            render: (row) => (
              <span
                className={cn(
                  "font-mono",
                  row.position === 1 && "text-primary",
                  row.status === "disqualified" && "text-danger"
                )}
                title={row.status === "disqualified" ? row.reason : undefined}
              >
                {getRaceGapLabel(row.status, row.gap)}
              </span>
            )
          },
          {
            key: "points",
            header: "Очк",
            align: "right",
            render: (row) => <span className="race-results-points">{row.points}</span>
          }
        ]}
      />
    </div>
  );
}

export function RaceResultsPage() {
  const { id: historicalStageId } = useParams<{ id: string }>();
  const isHistorical = Boolean(historicalStageId);
  const attemptedRaceRestoreRef = useRef(false);
  const navigate = useNavigate();
  const selectedTeamId = useSeasonStore((state) => state.selectedTeamId);
  const selectedDriverIds = useSeasonStore((state) => state.selectedDriverIds);
  const stageProgress = useSeasonStore((state) => state.stageProgress);
  const restoreRaceResults = useSeasonStore((state) => state.restoreRaceResults);
  const isLoading = useSeasonStore((state) => state.isLoading);
  const errorCode = useSeasonStore((state) => state.errorCode);
  const errorMessage = useSeasonStore((state) => state.errorMessage);
  const activeStage = getCurrentStage();
  const stages = seasonRepository.getStages();
  const cachedRaceResults = seasonRepository.getRaceResults();
  const latestResultStage = cachedRaceResults.length
    ? stages
        .filter((item) => cachedRaceResults.some((result) => result.stageId === item.id))
        .sort((left, right) => right.stageNumber - left.stageNumber)[0]
    : undefined;
  const latestCompletedRaceStage = stages
    .filter((item) =>
      stageProgress.some(
        (progress) => progress.stageId === item.id && progress.raceStatus === "completed"
      )
    )
    .sort((left, right) => right.stageNumber - left.stageNumber)[0];
  const historicalStage = historicalStageId
    ? stages.find((item) => item.id === historicalStageId)
    : undefined;
  const isHistoricalStageMissing = isHistorical && !historicalStage;
  const stage = historicalStage ?? latestResultStage ?? latestCompletedRaceStage ?? activeStage;
  const track = getTrack(stage.trackId);
  const selectedTeam = selectedTeamId ? getTeam(selectedTeamId) : getTeam("");
  const raceResults = isHistoricalStageMissing
    ? []
    : seasonRepository.getRaceResultsByStage(stage.id);
  const qualifyingResults = isHistoricalStageMissing
    ? []
    : seasonRepository.getQualifyingResultsByStage(stage.id);
  const currentProgress = stageProgress.find((progress) => progress.stageId === stage.id);
  const raceStatus = currentProgress?.raceStatus ?? "locked";
  const hasBlockingError = Boolean(errorMessage && errorCode !== "ENTITY_NOT_FOUND");
  const shouldRedirectToGrid =
    !isHistorical &&
    !raceResults.length &&
    raceStatus !== "completed" &&
    !isLoading &&
    !hasBlockingError;

  useEffect(() => {
    void useSeasonStore
      .getState()
      .refreshSeason()
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (shouldRedirectToGrid) {
      navigate(ROUTES.raceGrid, { replace: true });
    }
  }, [navigate, shouldRedirectToGrid]);

  useEffect(() => {
    if (isHistoricalStageMissing) return;
    if (raceStatus !== "completed") {
      attemptedRaceRestoreRef.current = false;
      return;
    }

    if (raceResults.length || isLoading || errorMessage) return;
    if (attemptedRaceRestoreRef.current) return;

    attemptedRaceRestoreRef.current = true;
    void restoreRaceResults(stage.id).catch(() => undefined);
  }, [
    errorMessage,
    isHistoricalStageMissing,
    isLoading,
    raceResults.length,
    raceStatus,
    restoreRaceResults,
    stage.id
  ]);

  function openStandings() {
    navigate(ROUTES.championshipSummary);
  }

  if (isHistoricalStageMissing) {
    return (
      <PageSurface className="mx-auto flex min-h-[calc(100dvh-8rem)] w-full items-center justify-center">
        <div className="race-panel max-w-md p-6 text-center">
          <p className="metadata-label">Результаты недоступны</p>
          <p className="mt-2 font-mono text-sm uppercase text-muted-foreground">
            Этап не найден в календаре.
          </p>
          <Button className="mt-4" onClick={() => navigate(ROUTES.seasonOverview)}>
            К календарю
          </Button>
        </div>
      </PageSurface>
    );
  }

  if (isHistorical && !isLoading && !raceResults.length) {
    return (
      <PageSurface className="mx-auto flex min-h-[calc(100dvh-8rem)] w-full items-center justify-center">
        <div className="race-panel max-w-md p-6 text-center">
          <p className="metadata-label">Нет данных</p>
          <p className="mt-2 font-mono text-sm uppercase text-muted-foreground">
            Результаты этого этапа недоступны.
          </p>
          <Button className="mt-4" onClick={() => navigate(ROUTES.seasonOverview)}>
            К календарю
          </Button>
        </div>
      </PageSurface>
    );
  }

  return (
    <PageSurface className="mx-auto flex min-h-[calc(100dvh-8rem)] w-full flex-col overflow-hidden">
      <PageHeader
        title={getGrandPrixTitle(track)}
        actions={
          <Button type="button" onClick={openStandings}>
            Открыть зачеты
          </Button>
        }
        meta={
          <InfoChip
            {...(stage.id === activeStage.id && !isHistorical
              ? getCurrentStageMeta(stage, track)
              : getStageMeta(stage, track))}
          />
        }
      />

      {selectedTeamId && !isHistorical ? <CarConditionPanel /> : null}

      <section className="race-weekend-stage">
        <div className="unified-race-board">
          <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
            <RaceResultsGrid rows={raceResults} selectedTeamId={selectedTeamId} />

            <RaceContextPanel
              track={track}
              selectedTeam={selectedTeam}
              selectedDriverIds={selectedDriverIds}
              isResultsView
              gridRows={qualifyingResults}
              raceResults={raceResults}
              weather={stage.weather}
            />
          </div>
        </div>
      </section>
    </PageSurface>
  );
}
