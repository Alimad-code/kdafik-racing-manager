import { Play, RotateCcw, Save } from "lucide-react";
import { Navigate, useNavigate } from "react-router-dom";
import type { PracticeSegment } from "@/entities";
import {
  getPracticeProgram,
  getPracticeSegmentStatus,
  hasCompletedPracticeSegment,
  practiceSegmentLabels,
  practiceSegments
} from "@/features/season/lib/practiceProgram";
import {
  formatMoney,
  formatTrackProfile,
  formatWeather,
  getCurrentStage,
  getDriver,
  getTeam,
  getTrack
} from "@/features/season/lib/seasonViewData";
import { useSeasonStore } from "@/features/season/model/useSeasonStore";
import { CarConditionPanel } from "@/features/season/ui/CarConditionPanel";
import { ROUTES } from "@/shared/constants/routes";
import { cn } from "@/shared/lib/utils";
import { getCurrentStageMeta } from "@/pages/_shared/race-weekend";
import {
  Button,
  ButtonLink,
  ActionPanel,
  InfoChip,
  MetricRow,
  PageHeader,
  PageSurface,
  SectionHeader,
  StatBlock,
  TrackMap
} from "@/shared/ui";

export function PracticeSetupPage() {
  const navigate = useNavigate();
  const selectedTeamId = useSeasonStore((state) => state.selectedTeamId);
  const selectedDriverIds = useSeasonStore((state) => state.selectedDriverIds);
  const cars = useSeasonStore((state) => state.cars);
  const originalCars = useSeasonStore((state) => state.originalCars);
  const stageProgress = useSeasonStore((state) => state.stageProgress);
  const setCarSetup = useSeasonStore((state) => state.setCarSetup);
  const resetCarSetup = useSeasonStore((state) => state.resetCarSetup);
  const runPracticeSegment = useSeasonStore((state) => state.runPracticeSegment);
  const completePractice = useSeasonStore((state) => state.completePractice);
  const budget = useSeasonStore((state) => state.budget);
  const isLoading = useSeasonStore((state) => state.isLoading);
  const stage = getCurrentStage();
  const track = getTrack(stage.trackId);
  const team = selectedTeamId ? getTeam(selectedTeamId) : null;
  const currentProgress = stageProgress.find((progress) => progress.stageId === stage.id);
  const practiceProgram = getPracticeProgram(stage.id, currentProgress);
  const qualifyingStatus = currentProgress?.qualifyingStatus ?? "locked";
  const hasConfirmedRoster = Boolean(selectedTeamId && selectedDriverIds.length === 2);
  const hasTwoCars = cars.length === 2;
  const hasHeavilyDamagedCar = cars.some((car) => car.condition === "heavily-damaged");
  const setupUnitCost = team?.setupCost ?? 0;
  const changedCarsCount = cars.filter((car) => {
    const originalCar = originalCars.find((item) => item.id === car.id);
    return (
      originalCar &&
      (car.wingsSetting !== originalCar.wingsSetting ||
        car.suspensionSetting !== originalCar.suspensionSetting ||
        car.gearboxSetting !== originalCar.gearboxSetting)
    );
  }).length;
  const totalSetupCost = changedCarsCount * setupUnitCost;
  const availableForSetup = budget.setupReserveMillions + budget.freeMillions;
  const hasEnoughFundsForSetup = totalSetupCost <= availableForSetup;
  const setupReserveAfterForecast = Math.max(budget.setupReserveMillions - totalSetupCost, 0);
  const freeFundsUsedForecast = Math.max(totalSetupCost - budget.setupReserveMillions, 0);
  const freeBudgetAfterForecast = Math.max(budget.freeMillions - freeFundsUsedForecast, 0);
  const completedSegmentsCount = practiceSegments.filter(
    (segment) => getPracticeSegmentStatus(practiceProgram, segment) === "completed"
  ).length;
  const availableSegments = practiceSegments.filter(
    (segment) => getPracticeSegmentStatus(practiceProgram, segment) === "available"
  );
  const nextAvailableSegment = availableSegments[0];
  const displayedPracticeSegment = nextAvailableSegment ?? "fp3";
  const displayedWeather = stage.weather?.practice[displayedPracticeSegment];
  const canCompletePractice =
    hasConfirmedRoster &&
    hasTwoCars &&
    hasCompletedPracticeSegment(practiceProgram) &&
    practiceProgram.practiceCompletionStatus === "available";

  async function launchSegment(segment: PracticeSegment) {
    try {
      await runPracticeSegment(segment);
      navigate(ROUTES.practiceResults);
    } catch {
      // Backend error details are kept in the store and rendered below.
    }
  }

  async function finishPractice() {
    try {
      await completePractice();
      navigate(ROUTES.qualifying);
    } catch {
      // Backend error details are kept in the store and rendered below.
    }
  }

  if (practiceProgram.practiceCompletionStatus === "completed") {
    return (
      <Navigate
        replace
        to={qualifyingStatus === "completed" ? ROUTES.qualifyingResults : ROUTES.qualifying}
      />
    );
  }

  if (!hasConfirmedRoster || !hasTwoCars) {
    const description = hasConfirmedRoster
      ? "Команда подтверждена, но для программы практики нужны два активных болида."
      : "Настройка практики открывается после выбора команды и двух пилотов.";

    return (
      <PageSurface>
        <PageHeader
          title="Настройка практики"
          description={description}
          actions={<ButtonLink to={ROUTES.seasonOverview}>Открыть календарь</ButtonLink>}
          meta={
            <>
              <InfoChip {...getCurrentStageMeta(stage, track)} />
              <InfoChip label="Состав" value={hasConfirmedRoster ? "Утвержден" : "Не утвержден"} />
              <InfoChip label="Болиды" value={`${cars.length}/2 готовы`} />
            </>
          }
        />
        <TrackMap
          aria-label={`Карта трассы ${track.name}`}
          className="mt-4 h-40"
          label={track.name}
          svgPath={track.svgPath}
          trackWetness={displayedWeather?.trackWetness}
          variant="panel"
        />
      </PageSurface>
    );
  }

  return (
    <PageSurface>
      <PageHeader
        title="Настройка практики"
        description="Проведите практику для обратной связи или завершите программу, когда настройки уже устраивают."
        actions={
          <>
            {nextAvailableSegment ? (
              <>
                <Button
                  disabled={isLoading || !hasEnoughFundsForSetup || hasHeavilyDamagedCar}
                  type="button"
                  onClick={() => launchSegment(nextAvailableSegment)}
                >
                  <Play className="size-4" />
                  {isLoading
                    ? "Сохраняем..."
                    : `Запустить ${practiceSegmentLabels[nextAvailableSegment]}`}
                </Button>
                {canCompletePractice ? (
                  <Button
                    disabled={isLoading || !hasEnoughFundsForSetup || hasHeavilyDamagedCar}
                    type="button"
                    variant="secondary"
                    onClick={finishPractice}
                  >
                    <Save className="size-4" />
                    Завершить практику
                  </Button>
                ) : null}
              </>
            ) : canCompletePractice ? (
              <Button
                disabled={isLoading || !hasEnoughFundsForSetup || hasHeavilyDamagedCar}
                type="button"
                onClick={finishPractice}
              >
                <Save className="size-4" />
                {isLoading ? "Фиксируем..." : "Завершить практику"}
              </Button>
            ) : (
              <ButtonLink to={ROUTES.practiceResults}>Отчеты П</ButtonLink>
            )}
            {completedSegmentsCount > 0 && (nextAvailableSegment || canCompletePractice) ? (
              <ButtonLink to={ROUTES.practiceResults} variant="secondary">
                Отчеты П
              </ButtonLink>
            ) : null}
          </>
        }
        meta={
          <>
            <InfoChip {...getCurrentStageMeta(stage, track)} />
            <InfoChip label="Проведённые практики" value={`${completedSegmentsCount}/3`} />
          </>
        }
      />

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <StatBlock
          label="Трасса"
          value={track.name}
          detail={`${formatTrackProfile(track.profile)} / ${formatWeather(displayedWeather?.precipitation ?? "none")}`}
        />
        <StatBlock
          label="Доступно для настройки"
          value={
            formatMoney(budget.setupReserveMillions) + " + " + formatMoney(budget.freeMillions)
          }
          detail="Фонд настроек + свободные деньги"
        />
        <StatBlock
          label="Стоимость изменений"
          value={formatMoney(totalSetupCost)}
          detail={
            changedCarsCount
              ? `Изменено болидов: ${changedCarsCount}`
              : "Настройки не изменены, списание не требуется"
          }
        />
        <StatBlock
          label="После сохранения"
          value={
            hasEnoughFundsForSetup
              ? formatMoney(setupReserveAfterForecast) + " + " + formatMoney(budget.freeMillions)
              : "Недостаточно средств"
          }
          detail={
            hasEnoughFundsForSetup
              ? freeFundsUsedForecast > 0
                ? `Фонд настроек исчерпан; из свободных уйдет ${formatMoney(freeFundsUsedForecast)}, останется ${formatMoney(freeBudgetAfterForecast)}`
                : "Остаток фонда настроек и свободных денег."
              : "Уменьшите число изменённых болидов"
          }
        />
        <TrackMap
          aria-label={`Карта трассы ${track.name}`}
          svgPath={track.svgPath}
          trackWetness={displayedWeather?.trackWetness}
          variant="panel"
        />
      </section>

      <section className="space-y-4">
        <CarConditionPanel />
        {hasHeavilyDamagedCar ? (
          <ActionPanel
            title="Практика заблокирована"
            description="Сильно повреждённый болид нужно отремонтировать до следующей сессии."
          />
        ) : null}
        <SectionHeader
          title="Инженерная наладка"
          description="Настройте три ключевых узла болида. Практика поможет сузить рабочий диапазон."
        />

        <div className="grid gap-4 md:grid-cols-2">
          {cars.map((car, index) => {
            const driver = getDriver(car.driverId);
            const originalCar = originalCars.find((item) => item.id === car.id);
            const isChanged =
              originalCar &&
              (car.wingsSetting !== originalCar.wingsSetting ||
                car.suspensionSetting !== originalCar.suspensionSetting ||
                car.gearboxSetting !== originalCar.gearboxSetting);

            return (
              <article key={car.id} className="race-panel p-4">
                <div className="space-y-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-3">
                      <div>
                        <p className="metadata-label">Болид {index + 1}</p>
                        <h3 className="mt-2 text-xl font-black uppercase text-foreground">
                          {driver.firstName} {driver.lastName}
                        </h3>
                      </div>
                      <div className="grid gap-3 sm">
                        <MetricRow
                          label="Профиль пилота"
                          value=""
                          detail={`Темп ${driver.pace} / Стабильность ${driver.stability}`}
                        />
                      </div>
                    </div>
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center">
                      {isChanged ? (
                        <Button
                          aria-label={`Сбросить настройки болида ${index + 1}`}
                          className="size-9 min-h-0 p-0 sm:min-h-0 sm:px-0 sm:py-0"
                          title="Сбросить настройки"
                          variant="secondary"
                          onClick={() => resetCarSetup(car.id)}
                        >
                          <RotateCcw aria-hidden="true" className="size-5 shrink-0" />
                        </Button>
                      ) : null}
                    </div>
                  </div>

                  <div className="grid gap-4 xl:grid-cols-3">
                    <div className="space-y-3">
                      <div className="flex items-end justify-between">
                        <p className="metadata-label">Аэродинамика</p>
                        <p className="font-mono text-xl font-bold">
                          {car.wingsSetting}
                          <span className="ml-1 text-sm text-muted-foreground">/100</span>
                        </p>
                      </div>
                      <input
                        className={cn(
                          "h-2 w-full cursor-pointer appearance-none bg-secondary accent-primary",
                          "[&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:bg-primary",
                          "[&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:bg-primary"
                        )}
                        max={100}
                        min={0}
                        type="range"
                        value={car.wingsSetting}
                        onChange={(e) => setCarSetup(car.id, { wings: Number(e.target.value) })}
                      />
                      <div className="flex justify-between text-[10px] font-bold uppercase text-muted-foreground">
                        <span>Скорость</span>
                        <span>Прижим</span>
                      </div>
                    </div>

                    <div className="space-y-3">
                      <div className="flex items-end justify-between">
                        <p className="metadata-label">Шасси</p>
                        <p className="font-mono text-xl font-bold">
                          {car.suspensionSetting}
                          <span className="ml-1 text-sm text-muted-foreground">/100</span>
                        </p>
                      </div>
                      <input
                        className={cn(
                          "h-2 w-full cursor-pointer appearance-none bg-secondary accent-primary",
                          "[&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:bg-primary",
                          "[&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:bg-primary"
                        )}
                        max={100}
                        min={0}
                        type="range"
                        value={car.suspensionSetting}
                        onChange={(e) =>
                          setCarSetup(car.id, { suspension: Number(e.target.value) })
                        }
                      />
                      <div className="flex justify-between text-[10px] font-bold uppercase text-muted-foreground">
                        <span>Мягкая</span>
                        <span>Жесткая</span>
                      </div>
                    </div>

                    <div className="space-y-3">
                      <div className="flex items-end justify-between">
                        <p className="metadata-label">Трансмиссия</p>
                        <p className="font-mono text-xl font-bold">
                          {car.gearboxSetting}
                          <span className="ml-1 text-sm text-muted-foreground">/100</span>
                        </p>
                      </div>
                      <input
                        className={cn(
                          "h-2 w-full cursor-pointer appearance-none bg-secondary accent-primary",
                          "[&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:bg-primary",
                          "[&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:bg-primary"
                        )}
                        max={100}
                        min={0}
                        type="range"
                        value={car.gearboxSetting}
                        onChange={(e) => setCarSetup(car.id, { gearbox: Number(e.target.value) })}
                      />
                      <div className="flex justify-between text-[10px] font-bold uppercase text-muted-foreground">
                        <span>Короткая</span>
                        <span>Длинная</span>
                      </div>
                    </div>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </PageSurface>
  );
}
