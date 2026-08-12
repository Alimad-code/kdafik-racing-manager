import { useEffect, useRef, type CSSProperties } from "react";
import { seasonRepository } from "@/features/season/api/seasonDataSource";
import {
  formatDriverName,
  getCurrentStage,
  getTeam,
  getTrack
} from "@/features/season/lib/seasonViewData";
import { useSeasonStore } from "@/features/season/model/useSeasonStore";
import { ROUTES } from "@/shared/constants/routes";
import { formatPositionLabel } from "@/shared/lib/positionLabel";
import { getReadableTeamAccent } from "@/shared/lib/teamAccent";
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

const FALLBACK_TEAM_COLOR = "#64748b";

function getQualifyingLapLabel(status: string, bestLap?: string) {
  if (bestLap) {
    return bestLap;
  }

  if (status === "no-time") {
    return "Без времени";
  }

  if (status === "retired") {
    return "Сход";
  }

  return "-";
}

function getQualifyingGapLabel(status: string, gap: string) {
  if (status === "no-time") {
    return "Без времени";
  }

  if (status === "retired") {
    return "Сход";
  }

  return gap;
}

export function QualifyingResultsPage() {
  const attemptedRestoreRef = useRef(false);
  const selectedDriverIds = useSeasonStore((state) => state.selectedDriverIds);
  const stageProgress = useSeasonStore((state) => state.stageProgress);
  const restoreQualifyingResults = useSeasonStore((state) => state.restoreQualifyingResults);
  const isLoading = useSeasonStore((state) => state.isLoading);
  const errorCode = useSeasonStore((state) => state.errorCode);
  const errorMessage = useSeasonStore((state) => state.errorMessage);
  const stage = getCurrentStage();
  const track = getTrack(stage.trackId);
  const qualifyingWeather = stage.weather?.qualifying;
  const currentProgress = stageProgress.find((progress) => progress.stageId === stage.id);
  const practiceStatus = currentProgress?.practiceStatus ?? "locked";
  const qualifyingStatus = currentProgress?.qualifyingStatus ?? "locked";
  const raceStatus = currentProgress?.raceStatus ?? "locked";
  const qualifyingResults = seasonRepository.getQualifyingResultsByStage(stage.id);
  const pole = qualifyingResults[0];
  const userRows = qualifyingResults.filter((result) =>
    selectedDriverIds.includes(result.driverId)
  );
  const userGrid = userRows
    .map((result) => `${formatDriverName(result.driverId)} ${formatPositionLabel(result.position)}`)
    .join(" / ");
  const canOpenRaceRoute = qualifyingStatus === "completed" && qualifyingResults.length > 0;

  useEffect(() => {
    if (qualifyingStatus !== "completed") {
      attemptedRestoreRef.current = false;
      return;
    }

    if (
      qualifyingStatus === "completed" &&
      !qualifyingResults.length &&
      !isLoading &&
      !errorMessage
    ) {
      if (attemptedRestoreRef.current) {
        return;
      }

      attemptedRestoreRef.current = true;
      void restoreQualifyingResults().catch(() => undefined);
    }
  }, [
    errorMessage,
    isLoading,
    qualifyingResults.length,
    qualifyingStatus,
    restoreQualifyingResults
  ]);

  if (!pole) {
    const hasBlockingError = Boolean(errorMessage && errorCode !== "ENTITY_NOT_FOUND");
    const isRestoringSavedProtocol = qualifyingStatus === "completed" && isLoading;
    const emptyDescription = hasBlockingError
      ? (errorMessage ?? "Потеряна связь с гоночной дирекцией при чтении итогов квалификации.")
      : isRestoringSavedProtocol
        ? "Загружаем стартовую решетку из архива."
        : qualifyingStatus === "completed"
          ? "Результаты еще не сформированы. Дирекция подтверждает финиш, но протокол пока не доступен."
          : practiceStatus !== "completed"
            ? "Квалификация заблокирована. Сначала завершите практику текущего этапа."
            : "Квалификация еще не запущена. Перейдите в брифинг и запустите сессию явно.";

    return (
      <PageSurface>
        <PageHeader
          title="Итоги квалификации"
          actions={
            <ButtonLink
              to={practiceStatus === "completed" ? ROUTES.qualifying : ROUTES.practiceSetup}
            >
              {practiceStatus === "completed" ? "Открыть квалификацию" : "Настроить практику"}
            </ButtonLink>
          }
          meta={
            <>
              <InfoChip {...getCurrentStageMeta(stage, track)} />
              <InfoChip
                label="Статус"
                value={qualifyingStatus === "completed" ? "Ожидание" : "Не запущен"}
              />
            </>
          }
        />
        <TrackMap
          aria-label={`Карта трассы ${track.name}`}
          className="mt-4 h-40"
          label={track.name}
          svgPath={track.svgPath}
          trackWetness={qualifyingWeather?.trackWetness}
          variant="panel"
        />
        <ActionPanel
          title={hasBlockingError ? "Системная ошибка" : "Протокол недоступен"}
          description={
            hasBlockingError
              ? (emptyDescription ?? "Потеряна связь при получении данных.")
              : "Эта страница читает только официальный протокол квалификации. Она не создает временную решетку до завершения заездов."
          }
        >
          <ButtonLink
            to={practiceStatus === "completed" ? ROUTES.qualifying : ROUTES.practiceSetup}
          >
            {practiceStatus === "completed" ? "Брифинг квалификации" : "Настройка практики"}
          </ButtonLink>
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
        title={`Итоги квалификации: ${track.name}`}
        actions={
          <>
            {canOpenRaceRoute ? (
              <ButtonLink to={raceStatus === "completed" ? ROUTES.raceResults : ROUTES.raceGrid}>
                {raceStatus === "completed" ? "Открыть итоги гонки" : "Перейти к гонке"}
              </ButtonLink>
            ) : (
              <ButtonLink to={ROUTES.qualifying}>Вернуться в брифинг</ButtonLink>
            )}
          </>
        }
        meta={
          <>
            <InfoChip {...getCurrentStageMeta(stage, track)} />
          </>
        }
      />

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <StatBlock
          label="Поул"
          value={formatDriverName(pole.driverId) + " - " + (pole.bestLap ?? "-")}
          detail={`${getTeam(pole.teamId).name}`}
          accent={getTeam(pole.teamId).color}
        />
        <StatBlock
          label="Решетка команды"
          value={userGrid || "-"}
          accent={getTeam(useSeasonStore.getState().selectedTeamId ?? "").color}
        />
        <TrackMap
          aria-label={`Карта трассы ${track.name}`}
          svgPath={track.svgPath}
          trackWetness={qualifyingWeather?.trackWetness}
          variant="panel"
        />
      </section>

      <div className="grid min-w-0 gap-5 xl">
        <section className="min-w-0 space-y-4">
          <SectionHeader title="Стартовая решетка" />
          <TimingTable
            density="compact"
            rows={qualifyingResults}
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
                header: "Старт",
                headerClassName: "w-16",
                cellClassName: "w-16",
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
                key: "lap",
                header: "Лучший",
                align: "right",
                render: (row) => (
                  <span className="timing-value">
                    {getQualifyingLapLabel(row.status, row.bestLap)}
                  </span>
                )
              },
              {
                key: "gap",
                header: "Отст.",
                align: "right",
                render: (row) => (
                  <span className="font-mono">{getQualifyingGapLabel(row.status, row.gap)}</span>
                )
              }
            ]}
          />
        </section>
      </div>
    </PageSurface>
  );
}
