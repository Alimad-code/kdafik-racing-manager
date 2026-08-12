import { useNavigate } from "react-router-dom";
import { getPracticeProgram } from "@/features/season/lib/practiceProgram";
import { formatWeather, getCurrentStage, getTrack } from "@/features/season/lib/seasonViewData";
import { useSeasonStore } from "@/features/season/model/useSeasonStore";
import { CarConditionPanel } from "@/features/season/ui/CarConditionPanel";
import { ROUTES } from "@/shared/constants/routes";
import { getCurrentStageMeta } from "@/pages/_shared/race-weekend";
import {
  Button,
  ButtonLink,
  InfoChip,
  PageHeader,
  PageSurface,
  StatBlock,
  TrackMap
} from "@/shared/ui";

export function QualifyingPage() {
  const navigate = useNavigate();
  const selectedDriverIds = useSeasonStore((state) => state.selectedDriverIds);
  const selectedTeamId = useSeasonStore((state) => state.selectedTeamId);
  const cars = useSeasonStore((state) => state.cars);
  const stageProgress = useSeasonStore((state) => state.stageProgress);
  const runQualifying = useSeasonStore((state) => state.runQualifying);
  const isLoading = useSeasonStore((state) => state.isLoading);
  const stage = getCurrentStage();
  const track = getTrack(stage.trackId);
  const qualifyingWeather = stage.weather?.qualifying;
  const currentProgress = stageProgress.find((progress) => progress.stageId === stage.id);
  const practiceProgram = getPracticeProgram(stage.id, currentProgress);
  const qualifyingStatus = currentProgress?.qualifyingStatus ?? "locked";
  const hasConfirmedRoster = Boolean(selectedTeamId && selectedDriverIds.length === 2);
  const hasTwoCars = cars.length === 2;
  const practiceCompleted = practiceProgram.practiceCompletionStatus === "completed";
  const qualifyingCompleted = qualifyingStatus === "completed";
  const hasHeavilyDamagedCar = cars.some((car) => car.condition === "heavily-damaged");
  const carsReady = hasTwoCars && !hasHeavilyDamagedCar;
  const canStartQualifying =
    hasConfirmedRoster && hasTwoCars && practiceCompleted && carsReady && !qualifyingCompleted;

  async function startQualifying() {
    try {
      await runQualifying();
      navigate(ROUTES.qualifyingResults);
    } catch {
      // Backend error details are kept in the store and rendered below.
    }
  }

  return (
    <PageSurface>
      <PageHeader
        title={`Квалификация: ${track.name}`}
        actions={
          <>
            {qualifyingCompleted ? (
              <ButtonLink to={ROUTES.qualifyingResults}>Открыть решетку</ButtonLink>
            ) : !practiceCompleted ? (
              <ButtonLink to={ROUTES.practiceSetup}>Завершить практику</ButtonLink>
            ) : (
              <Button
                disabled={!canStartQualifying || isLoading}
                type="button"
                onClick={startQualifying}
              >
                {isLoading ? "Сохраняем..." : "Запустить квалификацию"}
              </Button>
            )}
          </>
        }
        meta={
          <>
            <InfoChip {...getCurrentStageMeta(stage, track)} />
          </>
        }
      />

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-2">
        <StatBlock
          label="Условия"
          value={formatWeather(qualifyingWeather?.precipitation ?? "none")}
          detail={`${track.climate.trackTemperatureMinC}–${track.climate.trackTemperatureMaxC} °C`}
        />
        <TrackMap
          aria-label={`Карта трассы ${track.name}`}
          svgPath={track.svgPath}
          trackWetness={qualifyingWeather?.trackWetness}
          variant="panel"
        />
      </section>

      <CarConditionPanel />
    </PageSurface>
  );
}
