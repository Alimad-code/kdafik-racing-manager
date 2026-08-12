import type { SeasonStage, SeasonStageStatus, StageSessionProgress } from "@/entities";
import { seasonRepository } from "@/features/season/api/seasonDataSource";
import { getNextPracticeStep, getPracticeProgram } from "@/features/season/lib/practiceProgram";
import { useSeasonStore } from "@/features/season/model/useSeasonStore";
import { CarConditionPanel } from "@/features/season/ui/CarConditionPanel";
import { getCurrentStage, getTeam, getTrack } from "@/features/season/lib/seasonViewData";
import type { AppRoute } from "@/shared/constants/routes";
import { ROUTES } from "@/shared/constants/routes";
import { cn } from "@/shared/lib/utils";
import {
  ButtonLink,
  InfoChip,
  PageHeader,
  PageSurface,
  SectionHeader,
  StageStatusPill,
  TrackMap
} from "@/shared/ui";

type NextSeasonAction = {
  label: string;
  to: AppRoute;
  detail: string;
};

function getStageProgress(
  stageId: string,
  stageProgress: StageSessionProgress[]
): StageSessionProgress | undefined {
  return stageProgress.find((progress) => progress.stageId === stageId);
}

function getStageDisplayStatus(
  stage: SeasonStage,
  progress: StageSessionProgress | undefined,
  currentStageId: string
): SeasonStageStatus {
  if (progress?.raceStatus === "completed" || stage.status === "completed") {
    return "completed";
  }

  if (stage.id === currentStageId || stage.status === "available") {
    return "available";
  }

  return "locked";
}

function getNextSeasonAction(
  hasConfirmedRoster: boolean,
  progress: StageSessionProgress | undefined,
  currentStageStatus: SeasonStageStatus,
  isSeasonFinished: boolean
): NextSeasonAction {
  if (!hasConfirmedRoster) {
    return {
      label: "Утвердить состав",
      to: ROUTES.seasonSetup,
      detail: "Перед календарем нужно выбрать команду и двух пилотов."
    };
  }

  if (isSeasonFinished) {
    return {
      label: "Итоги сезона",
      to: ROUTES.championshipSummary,
      detail: "Все этапы завершены. Проверьте финальные зачеты чемпионата."
    };
  }

  if (currentStageStatus === "completed") {
    return {
      label: "Следующий этап",
      to: ROUTES.seasonOverview,
      detail: "Этап завершен. Перейдите к следующему в календаре."
    };
  }

  const practiceProgram = getPracticeProgram("", progress);
  const nextPracticeStep = getNextPracticeStep(practiceProgram);

  if (!progress || progress.practiceStatus !== "completed") {
    const practiceLabel =
      nextPracticeStep.kind === "segment"
        ? `Запустить ${nextPracticeStep.label}`
        : nextPracticeStep.kind === "final"
          ? "Завершить практику"
          : "Практика";

    return {
      label: practiceLabel,
      to: ROUTES.practiceSetup,
      detail:
        nextPracticeStep.kind === "final"
          ? "Завершите программу практики, чтобы открыть квалификацию."
          : "Следующее действие: программа свободных заездов активного этапа."
    };
  }

  if (progress.qualifyingStatus !== "completed") {
    return {
      label: "К квалификации",
      to: ROUTES.qualifying,
      detail: "Практика завершена. Следующий шаг: квалификация."
    };
  }

  if (progress.raceStatus !== "completed") {
    return {
      label: "Открыть гонку",
      to: ROUTES.raceGrid,
      detail: "Квалификация завершена. Следующий шаг: гоночный протокол."
    };
  }

  return {
    label: "Открыть зачеты",
    to: ROUTES.championshipSummary,
    detail: "Этап завершен. Итоги доступны в таблицах чемпионата."
  };
}

function getCompletedStagesCount(stages: SeasonStage[], stageProgress: StageSessionProgress[]) {
  return stages.filter((stage) => {
    const progress = getStageProgress(stage.id, stageProgress);
    return stage.status === "completed" || progress?.raceStatus === "completed";
  }).length;
}

function getStageCtaLabel(nextAction: NextSeasonAction) {
  if (nextAction.to === ROUTES.practiceSetup) {
    return "Перейти к практике";
  }

  return nextAction.label;
}

export function SeasonOverviewPage() {
  const currentStageId = useSeasonStore((state) => state.currentStageId);
  const stageProgress = useSeasonStore((state) => state.stageProgress);
  const selectedTeamId = useSeasonStore((state) => state.selectedTeamId);
  const selectedDriverIds = useSeasonStore((state) => state.selectedDriverIds);
  const currentStage = getCurrentStage();
  const currentTrack = getTrack(currentStage.trackId);
  const stages = seasonRepository.getStages();
  const currentProgress = getStageProgress(currentStage.id, stageProgress);
  const hasConfirmedRoster = Boolean(selectedTeamId && selectedDriverIds.length === 2);
  const completedStagesCount = getCompletedStagesCount(stages, stageProgress);
  const isSeasonFinished = stages.length > 0 && completedStagesCount === stages.length;
  const nextAction = getNextSeasonAction(
    hasConfirmedRoster,
    currentProgress,
    currentStage.status,
    isSeasonFinished
  );
  const nextActionLabel = getStageCtaLabel(nextAction);
  const selectedTeam = selectedTeamId ? getTeam(selectedTeamId) : null;

  return (
    <PageSurface>
      <PageHeader
        title="Календарь этапов"
        actions={
          <>
            <ButtonLink to={ROUTES.home} variant="secondary">
              Главная панель
            </ButtonLink>
          </>
        }
        meta={
          <>
            <InfoChip
              label={isSeasonFinished ? "Финал" : "Текущий этап"}
              value={
                isSeasonFinished
                  ? "Сезон завершен"
                  : `${currentStage.stageNumber} · ${currentTrack.country}`
              }
            />
            <InfoChip label="Календарь" value={`${stages.length} этапов`} />
            <InfoChip label="Пройдено" value={`${completedStagesCount} / ${stages.length}`} />
          </>
        }
      />

      <section className="min-w-0 space-y-4">
        {selectedTeam ? <CarConditionPanel /> : null}
        <SectionHeader title="Доска календаря" />
        <div className="grid min-w-0 gap-3 md:grid-cols-2 2xl:grid-cols-3">
          {stages.map((stage) => {
            const track = getTrack(stage.trackId);
            const progress = getStageProgress(stage.id, stageProgress);
            const displayStatus = getStageDisplayStatus(stage, progress, currentStageId);
            const isActive = displayStatus === "available";
            const isCompleted = displayStatus === "completed";
            const isLocked = displayStatus === "locked";

            return (
              <article
                key={stage.id}
                className={cn(
                  "race-panel grid min-h-[150px] gap-3 p-3 transition sm:h-[158px]",
                  isActive && "border-primary/60 bg-primary/10",
                  isCompleted && "bg-success/5",
                  isLocked && "opacity-75",
                  isActive
                    ? "md:col-span-2 md:grid-cols-[minmax(0,1fr)_132px_auto] md:items-stretch 2xl:col-span-2"
                    : "grid-cols-[minmax(0,1fr)_112px] items-stretch"
                )}
              >
                {isActive ? (
                  <>
                    <div className="flex min-w-0 flex-col justify-center gap-3">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="metadata-label">Этап {stage.stageNumber}</p>
                          <StageStatusPill status={displayStatus} />
                        </div>
                        <h3 className="mt-2 line-clamp-2 text-xl font-black uppercase leading-tight text-foreground">
                          {`ЭТАП · ${track.country}`}
                        </h3>
                      </div>
                    </div>

                    <div className="order-first size-[112px] sm:size-auto md:order-none md:h-full md:w-full">
                      <TrackMap
                        aria-label={`Карта трассы ${track.name}`}
                        svgPath={track.svgPath}
                        variant="square"
                      />
                    </div>

                    <div className="flex items-end md:items-center md:justify-end">
                      <ButtonLink className="w-full md:w-auto" to={nextAction.to}>
                        {nextActionLabel}
                      </ButtonLink>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="flex min-w-0 flex-col justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="metadata-label">Этап {stage.stageNumber}</p>
                          <StageStatusPill status={displayStatus} />
                        </div>
                        <h3 className="mt-2 line-clamp-3 text-base font-black uppercase leading-tight text-foreground">
                          {`ЭТАП · ${track.country}`}
                        </h3>
                      </div>
                      <p className="font-mono text-[10px] font-black uppercase tracking-[0.16em] text-muted-foreground">
                        {isCompleted ? "Завершен" : "Закрыт"}
                      </p>
                      {isCompleted ? (
                        <ButtonLink
                          className="w-fit"
                          to={`/stage/${stage.id}/results`}
                          variant="secondary"
                        >
                          Результаты
                        </ButtonLink>
                      ) : null}
                    </div>

                    <div className="size-[112px] self-center justify-self-end">
                      <TrackMap
                        aria-label={`Карта трассы ${track.name}`}
                        svgPath={track.svgPath}
                        variant="square"
                      />
                    </div>
                  </>
                )}
              </article>
            );
          })}
        </div>
      </section>
    </PageSurface>
  );
}
