import { useEffect, useRef, useState, type CSSProperties } from "react";
import type { PracticeResult, PracticeSegment } from "@/entities";
import { seasonRepository } from "@/features/season/api/seasonDataSource";
import {
  getNextPracticeStep,
  getPracticeCompletionLabel,
  getPracticeProgram,
  getPracticeSegmentStatus,
  practiceSegmentLabels,
  practiceSegments
} from "@/features/season/lib/practiceProgram";
import {
  formatDriverName,
  getCurrentStage,
  getTeam,
  getTrack
} from "@/features/season/lib/seasonViewData";
import { useSeasonStore } from "@/features/season/model/useSeasonStore";
import { ROUTES } from "@/shared/constants/routes";
import { getReadableTeamAccent } from "@/shared/lib/teamAccent";
import { cn } from "@/shared/lib/utils";
import { getCurrentStageMeta } from "@/pages/_shared/race-weekend";
import {
  ActionPanel,
  ButtonLink,
  InfoChip,
  PageHeader,
  PageSurface,
  SectionHeader,
  StatBlock,
  TeamIcon,
  TimingTable,
  TrackMap
} from "@/shared/ui";
import { PracticeReportCards } from "./PracticeReportCards";

const FALLBACK_TEAM_COLOR = "#64748b";

function getPracticeBestLapLabel(bestLap?: string) {
  return bestLap ?? "Без времени";
}

function getPracticeGapLabel(status: string, gap: string) {
  if (status === "no-time") {
    return "Без времени";
  }

  if (status === "retired") {
    return "Сход";
  }

  return gap;
}

function getSegmentResults(rows: PracticeResult[], segment: PracticeSegment) {
  return rows.filter((row) => (row.practiceSegment ?? "fp1") === segment);
}

export function PracticeResultsPage() {
  const attemptedRestoreRef = useRef(false);
  const [selectedSegment, setSelectedSegment] = useState<PracticeSegment | undefined>(undefined);
  const selectedDriverIds = useSeasonStore((state) => state.selectedDriverIds);
  const selectedTeamId = useSeasonStore((state) => state.selectedTeamId);
  const stageProgress = useSeasonStore((state) => state.stageProgress);
  const restorePracticeProgram = useSeasonStore((state) => state.restorePracticeProgram);
  const isLoading = useSeasonStore((state) => state.isLoading);
  const errorCode = useSeasonStore((state) => state.errorCode);
  const errorMessage = useSeasonStore((state) => state.errorMessage);
  const stage = getCurrentStage();
  const track = getTrack(stage.trackId);
  const currentProgress = stageProgress.find((progress) => progress.stageId === stage.id);
  const practiceProgram = getPracticeProgram(stage.id, currentProgress);
  const nextPracticeStep = getNextPracticeStep(practiceProgram);
  const practiceResults = seasonRepository.getPracticeResultsByStage(stage.id);

  const completedSegmentsWithRows = practiceSegments.filter(
    (segment) =>
      getPracticeSegmentStatus(practiceProgram, segment) === "completed" &&
      getSegmentResults(practiceResults, segment).length > 0
  );
  const nextAvailableSegment = practiceSegments.find(
    (segment) => getPracticeSegmentStatus(practiceProgram, segment) === "available"
  );

  const activeSegment =
    selectedSegment && completedSegmentsWithRows.includes(selectedSegment)
      ? selectedSegment
      : (completedSegmentsWithRows.at(-1) ?? nextAvailableSegment);

  const activePracticeRows = activeSegment ? getSegmentResults(practiceResults, activeSegment) : [];
  const activeWeather = activeSegment ? stage.weather?.practice[activeSegment] : undefined;
  const leader = activePracticeRows[0];

  const hasConfirmedRoster = Boolean(selectedTeamId && selectedDriverIds.length === 2);
  const completedSegmentsCount = practiceSegments.filter(
    (segment) => getPracticeSegmentStatus(practiceProgram, segment) === "completed"
  ).length;
  const qualifyingStatus = currentProgress?.qualifyingStatus ?? "locked";
  const hasAvailableOptionalPractice = practiceSegments.some(
    (segment) =>
      segment !== "fp1" && getPracticeSegmentStatus(practiceProgram, segment) === "available"
  );
  const nextActionRoute =
    practiceProgram.practiceCompletionStatus === "completed"
      ? qualifyingStatus === "completed"
        ? ROUTES.qualifyingResults
        : ROUTES.qualifying
      : ROUTES.practiceSetup;
  const nextActionLabel =
    practiceProgram.practiceCompletionStatus === "completed"
      ? qualifyingStatus === "completed"
        ? "Итоги квалификации"
        : "Брифинг квалификации"
      : hasAvailableOptionalPractice
        ? "Вернуться к настройке"
        : nextPracticeStep.kind === "final"
          ? "Завершить практику"
          : "Продолжить практику";

  useEffect(() => {
    if (practiceResults.length || isLoading || errorMessage) {
      return;
    }

    if (attemptedRestoreRef.current) {
      return;
    }

    attemptedRestoreRef.current = true;
    void restorePracticeProgram().catch(() => undefined);
  }, [errorMessage, isLoading, practiceResults.length, restorePracticeProgram]);

  if (!leader) {
    const hasBlockingError = Boolean(errorMessage && errorCode !== "ENTITY_NOT_FOUND");
    const emptyDescription = hasBlockingError
      ? (errorMessage ?? "Потеряна связь при чтении отчетов практики.")
      : isLoading
        ? "Загружаем сохраненную программу практики."
        : "Практика еще не дала тайминга. Запустите обязательный П1 на экране настройки.";
    const actionRoute = hasConfirmedRoster ? nextActionRoute : ROUTES.seasonOverview;
    const actionLabel = hasConfirmedRoster ? nextActionLabel : "Открыть календарь";

    return (
      <PageSurface>
        <PageHeader
          title="Итоги практики"
          actions={<ButtonLink to={actionRoute}>{actionLabel}</ButtonLink>}
          meta={
            <>
              <InfoChip {...getCurrentStageMeta(stage, track)} />
              <InfoChip label="Программа" value={getPracticeCompletionLabel(practiceProgram)} />
            </>
          }
        />
        <TrackMap
          aria-label={`Карта трассы ${track.name}`}
          className="mt-4 h-40"
          label={track.name}
          svgPath={track.svgPath}
          trackWetness={activeWeather?.trackWetness}
          variant="panel"
        />
        <ActionPanel
          title={hasBlockingError ? "Системная ошибка" : "Тайминг недоступен"}
          description={
            hasBlockingError
              ? emptyDescription
              : "Эта страница показывает отчеты П1/П2/П3 после того, как хотя бы один выезд был проведен."
          }
        >
          <ButtonLink to={actionRoute}>{actionLabel}</ButtonLink>
          <ButtonLink to={ROUTES.seasonOverview} variant="secondary">
            Календарь сезона
          </ButtonLink>
        </ActionPanel>
      </PageSurface>
    );
  }

  return (
    <PageSurface>
      <PageHeader
        title="Итоги практики"
        actions={
          <>
            <ButtonLink to={nextActionRoute}>{nextActionLabel}</ButtonLink>
          </>
        }
        meta={
          <>
            <InfoChip {...getCurrentStageMeta(stage, track)} />
            <InfoChip label="Проведённые практики" value={`${completedSegmentsCount}/3`} />
          </>
        }
      />

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <StatBlock
          label="Лучший круг"
          value={formatDriverName(leader.driverId) + " - " + (leader.bestLap ?? "-")}
          detail={`${formatDriverName(leader.driverId)}, ${getTeam(leader.teamId).shortName}`}
          accent={getTeam(leader.teamId).color}
        />
        <StatBlock
          label="Проведено П"
          value={`${completedSegmentsCount}/3`}
          detail="Можно продолжить П2/П3 или завершить практику, если настройка уже устраивает."
        />
        <TrackMap
          aria-label={`Карта трассы ${track.name}`}
          svgPath={track.svgPath}
          trackWetness={activeWeather?.trackWetness}
          variant="panel"
        />
      </section>

      <div className="grid min-w-0 gap-5 xl">
        <section className="min-w-0 space-y-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <SectionHeader title="Протокол практики" />
            {completedSegmentsWithRows.length > 1 && (
              <div className="flex border border-border bg-muted/20 p-1">
                {completedSegmentsWithRows.map((segment) => (
                  <button
                    key={segment}
                    type="button"
                    onClick={() => setSelectedSegment(segment)}
                    className={cn(
                      "px-3 py-1.5 font-mono text-xs font-bold uppercase transition",
                      activeSegment === segment
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground"
                    )}
                  >
                    {practiceSegmentLabels[segment]}
                  </button>
                ))}
              </div>
            )}
          </div>
          <PracticeReportCards rows={activePracticeRows} driverIds={selectedDriverIds} />
          <TimingTable
            density="compact"
            rows={activePracticeRows}
            getRowKey={(row) => row.id}
            getRowClassName={(row) =>
              selectedDriverIds.includes(row.driverId)
                ? undefined
                : row.position === 1
                  ? "bg-success/5"
                  : row.status === "no-time"
                    ? "opacity-80"
                    : undefined
            }
            getRowStyle={(row) =>
              selectedDriverIds.includes(row.driverId)
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
                headerClassName: "w-12",
                cellClassName: "w-12",
                render: (row) => <span className="timing-value">{row.position}</span>
              },
              {
                key: "driver",
                header: "Пилот",
                render: (row) => (
                  <p className="font-black text-foreground">{formatDriverName(row.driverId)}</p>
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
                render: (row) => {
                  const team = getTeam(row.teamId);
                  return <span className="font-semibold text-foreground">{team.name}</span>;
                }
              },
              {
                key: "bestLap",
                header: "Лучший",
                align: "right",
                render: (row) => (
                  <span className="timing-value">{getPracticeBestLapLabel(row.bestLap)}</span>
                )
              },
              {
                key: "gap",
                header: "Отст.",
                align: "right",
                render: (row) => (
                  <span className="font-mono">{getPracticeGapLabel(row.status, row.gap)}</span>
                )
              }
            ]}
          />
        </section>
      </div>
    </PageSurface>
  );
}
