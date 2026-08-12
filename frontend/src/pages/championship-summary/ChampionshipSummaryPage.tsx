import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import type { Season, SeasonStage, StageSessionProgress } from "@/entities";
import { seasonRepository } from "@/features/season/api/seasonDataSource";
import { useSeasonStore } from "@/features/season/model/useSeasonStore";
import {
  getCurrentStage,
  formatDriverName,
  getTeam,
  getTrack,
  toConstructorRows,
  toStandingsRows
} from "@/features/season/lib/seasonViewData";
import { ROUTES } from "@/shared/constants/routes";
import { formatPositionLabel } from "@/shared/lib/positionLabel";
import {
  ActionPanel,
  Button,
  ButtonLink,
  InfoChip,
  PageHeader,
  PageSurface,
  StandingsTable,
  StatBlock,
  TeamIcon
} from "@/shared/ui";

function getStageProgress(
  stageId: string,
  stageProgress: StageSessionProgress[]
): StageSessionProgress | undefined {
  return stageProgress.find((progress) => progress.stageId === stageId);
}

function getCompletedStagesCount(stages: SeasonStage[], stageProgress: StageSessionProgress[]) {
  return stages.filter((stage) => {
    const progress = getStageProgress(stage.id, stageProgress);
    return stage.status === "completed" || progress?.raceStatus === "completed";
  }).length;
}

function getSeasonFinishedState(
  activeSeason: Season | null,
  stages: SeasonStage[],
  completedStagesCount: number
) {
  return (
    activeSeason?.status === "completed" ||
    (stages.length > 0 && completedStagesCount === stages.length)
  );
}

function getNextAction(
  activeSeason: Season | null,
  currentStage: SeasonStage,
  currentProgress: StageSessionProgress | undefined
) {
  if (!activeSeason?.selectedTeamId) {
    return {
      label: "Подтвердить состав",
      route: ROUTES.seasonSetup,
      detail: "Сезон еще не готов к спортивной программе."
    };
  }

  if (!currentProgress || currentProgress.practiceStatus !== "completed") {
    return {
      label: "Открыть практику",
      route: ROUTES.practiceSetup,
      detail: `Э${currentStage.stageNumber}: сначала нужен сохраненный протокол P.`
    };
  }

  if (currentProgress.qualifyingStatus !== "completed") {
    return {
      label: "Открыть квалификацию",
      route: ROUTES.qualifying,
      detail: `Э${currentStage.stageNumber}: следующий обязательный протокол - квалификация.`
    };
  }

  if (currentProgress.raceStatus !== "completed") {
    return {
      label: "Открыть гонку",
      route: ROUTES.raceResults,
      detail: `Э${currentStage.stageNumber}: запустите или восстановите протокол гонки.`
    };
  }

  return {
    label: "Календарь сезона",
    route: ROUTES.seasonOverview,
    detail: "Текущий этап закрыт. Следующее действие выбирается из календаря."
  };
}

function getPointsLabel(points?: number) {
  return `${points ?? 0} очков`;
}

export function ChampionshipSummaryPage() {
  const navigate = useNavigate();
  const selectedTeamId = useSeasonStore((state) => state.selectedTeamId);
  const selectedDriverIds = useSeasonStore((state) => state.selectedDriverIds);
  const stageProgress = useSeasonStore((state) => state.stageProgress);
  const loadStandings = useSeasonStore((state) => state.loadStandings);
  const startNewSeason = useSeasonStore((state) => state.startNewSeason);
  const isLoading = useSeasonStore((state) => state.isLoading);
  const errorMessage = useSeasonStore((state) => state.errorMessage);
  const standings = seasonRepository.getChampionshipStandings();
  const constructorStandings = seasonRepository.getConstructorStandings();
  const stages = seasonRepository.getStages();
  const activeSeason = seasonRepository.getActiveSeason();
  const driverLeader = standings[0];
  const constructorLeader = constructorStandings[0];
  const currentStage = getCurrentStage();
  const currentTrack = getTrack(currentStage.trackId);
  const currentProgress = getStageProgress(currentStage.id, stageProgress);
  const selectedTeam = getTeam(selectedTeamId ?? activeSeason?.selectedTeamId ?? "");
  const userConstructorStanding = selectedTeamId
    ? constructorStandings.find((row) => row.teamId === selectedTeamId)
    : undefined;
  const userDriverRows = standings.filter((row) => selectedDriverIds.includes(row.driverId));
  const completedStagesCount = getCompletedStagesCount(stages, stageProgress);
  const isSeasonFinished = getSeasonFinishedState(activeSeason, stages, completedStagesCount);
  const nextAction = getNextAction(activeSeason, currentStage, currentProgress);
  const hasStandings = standings.length > 0 || constructorStandings.length > 0;
  const progressLabel = stages.length
    ? `${completedStagesCount} / ${stages.length}`
    : "Календарь ожидается";
  const constructorRows = toConstructorRows(constructorStandings).map((row) => ({
    ...row,
    isHighlighted: row.participantId === selectedTeam.id
  }));
  const driverRows = toStandingsRows(standings).map((row) => {
    const isSelectedDriver = userDriverRows.some(
      (standing) => standing.driverId === row.participantId
    );

    return {
      ...row,
      isHighlighted: isSelectedDriver
    };
  });

  useEffect(() => {
    if ((!standings.length || !constructorStandings.length) && !isLoading && !errorMessage) {
      void loadStandings().catch(() => undefined);
    }
  }, [constructorStandings.length, errorMessage, isLoading, loadStandings, standings.length]);

  async function handleRestartSeason() {
    try {
      await startNewSeason();
      navigate(ROUTES.seasonSetup);
    } catch {
      // Store error state is rendered by the page; keep the user on the final report.
    }
  }

  if (!hasStandings) {
    const emptyDescription = errorMessage
      ? errorMessage
      : isLoading
        ? "Загружаем таблицы чемпионата."
        : "Итоговые таблицы чемпионата еще не сформированы.";

    return (
      <PageSurface>
        <PageHeader
          title="Зачёты чемпионата"
          description={emptyDescription}
          meta={<InfoChip label="Прогресс" value={progressLabel} />}
        />
        <ActionPanel
          title={errorMessage ? "Таблицы недоступны" : "Ожидание таблиц"}
          description={
            errorMessage
              ? "Страница не может отобразить зачеты из-за ошибки связи. Проверьте соединение или вернитесь к активному действию сезона."
              : "Зачеты появятся после первой проведенной гонки или обновления данных из гоночной дирекции."
          }
        >
          {isSeasonFinished ? (
            <RestartSeasonButton isLoading={isLoading} onRestart={handleRestartSeason} />
          ) : (
            <ButtonLink to={nextAction.route}>{nextAction.label}</ButtonLink>
          )}
          <ButtonLink to={ROUTES.seasonOverview} variant="secondary">
            Календарь
          </ButtonLink>
        </ActionPanel>
      </PageSurface>
    );
  }

  return (
    <PageSurface>
      <PageHeader
        title="Зачёты чемпионата"
        actions={
          <PageHeaderActions
            isSeasonFinished={isSeasonFinished}
            isLoading={isLoading}
            nextActionLabel={nextAction.label}
            nextActionRoute={nextAction.route}
            onRestartSeason={handleRestartSeason}
          />
        }
        meta={
          <>
            <InfoChip
              label={isSeasonFinished ? "Итоги" : "Текущий этап"}
              value={
                isSeasonFinished
                  ? `Сезон завершен`
                  : `${currentStage.stageNumber} · ${currentTrack.country}`
              }
            />
            <InfoChip label="Пройдено" value={progressLabel} />
          </>
        }
      />

      <section className="grid gap-4 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,0.65fr)]">
        <article className="race-panel border-l-2 border-l-primary bg-primary/10 p-5">
          <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <p className="metadata-label">Результат команды игрока</p>
              </div>
              <div className="mt-3 flex items-center gap-2">
                <h2 className="text-2xl font-black uppercase leading-tight text-foreground">
                  {selectedTeam.name}
                </h2>
                <TeamIcon className="size-5" color={selectedTeam.color} teamId={selectedTeam.id} />
              </div>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                {userConstructorStanding
                  ? `${selectedTeam.powerUnit}, ${selectedTeam.baseCountry}.`
                  : "Данные зачета для вашей команды еще не поступили."}
              </p>
            </div>
            <div className="shrink-0 text-left md:text-right">
              <p className="timing-value text-5xl">
                {formatPositionLabel(userConstructorStanding?.position)}
              </p>
              <p className="mt-2 font-mono text-sm font-black uppercase text-primary">
                {getPointsLabel(userConstructorStanding?.points)}
              </p>
            </div>
          </div>
          <div className="mt-5 grid gap-3 border-t border-border pt-4 sm:grid-cols-2">
            <MetricMini label="Победы" value={String(userConstructorStanding?.wins ?? 0)} />
            <MetricMini label="Подиумы" value={String(userConstructorStanding?.podiums ?? 0)} />
          </div>
        </article>

        <div className="grid gap-4">
          <StatBlock
            label="Лидер чемпионата"
            value={constructorLeader ? getTeam(constructorLeader.teamId).name : "-"}
            detail={
              constructorLeader ? getPointsLabel(constructorLeader.points) : "Ожидание данных"
            }
            accent={constructorLeader ? getTeam(constructorLeader.teamId).color : undefined}
          />
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <StatBlock
          label="Лидер пилотов"
          value={driverLeader ? formatDriverName(driverLeader.driverId) : "-"}
          detail={
            driverLeader
              ? `${driverLeader.points} очков, ${driverLeader.wins} побед, ${driverLeader.podiums} подиумов`
              : "Ожидание личного зачета"
          }
          accent={driverLeader ? getTeam(driverLeader.teamId).color : undefined}
        />
        <StatBlock
          label="Пилоты игрока"
          value={
            userDriverRows.length
              ? userDriverRows
                  .map(
                    (row) =>
                      `${formatDriverName(row.driverId)} ${formatPositionLabel(row.position)}`
                  )
                  .join(" / ")
              : "Пилоты не найдены в driver standings"
          }
          detail={
            userDriverRows.length
              ? userDriverRows.map((row) => getPointsLabel(row.points)).join(" / ")
              : "Ожидание личного зачета"
          }
          accent={selectedTeam.color}
        />
      </section>

      <div className="grid min-w-0 gap-5 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        <section className="min-w-0 space-y-4">
          <StandingsTable rows={constructorRows} caption="Кубок конструкторов" />
        </section>

        <section className="min-w-0 space-y-4">
          <StandingsTable rows={driverRows} caption="Личный зачет" />
        </section>
      </div>
    </PageSurface>
  );
}

type PageHeaderActionsProps = {
  isSeasonFinished: boolean;
  isLoading: boolean;
  nextActionLabel: string;
  nextActionRoute: string;
  onRestartSeason: () => void;
};

function PageHeaderActions({
  isSeasonFinished,
  isLoading,
  nextActionLabel,
  nextActionRoute,
  onRestartSeason
}: PageHeaderActionsProps) {
  if (isSeasonFinished) {
    return (
      <>
        <RestartSeasonButton isLoading={isLoading} onRestart={onRestartSeason} />
        <ButtonLink to={ROUTES.raceResults} variant="secondary">
          Итоги гонки
        </ButtonLink>
      </>
    );
  }

  return (
    <>
      <ButtonLink to={nextActionRoute}>{nextActionLabel}</ButtonLink>
      <ButtonLink to={ROUTES.seasonOverview} variant="secondary">
        Календарь
      </ButtonLink>
    </>
  );
}

type RestartSeasonButtonProps = {
  isLoading: boolean;
  onRestart: () => void;
};

function RestartSeasonButton({ isLoading, onRestart }: RestartSeasonButtonProps) {
  return (
    <Button disabled={isLoading} onClick={onRestart}>
      {isLoading ? "Запускаем сезон..." : "Начать новый сезон"}
    </Button>
  );
}

type MetricMiniProps = {
  label: string;
  value: string;
};

function MetricMini({ label, value }: MetricMiniProps) {
  return (
    <div className="border border-border bg-surface p-3">
      <p className="metadata-label">{label}</p>
      <p className="mt-2 timing-value text-xl">{value}</p>
    </div>
  );
}
