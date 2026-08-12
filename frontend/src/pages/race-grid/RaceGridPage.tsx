import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { seasonRepository } from "@/features/season/api/seasonDataSource";
import { getCurrentStage, getTeam, getTrack } from "@/features/season/lib/seasonViewData";
import { useSeasonStore } from "@/features/season/model/useSeasonStore";
import { CarConditionPanel } from "@/features/season/ui/CarConditionPanel";
import { ROUTES } from "@/shared/constants/routes";
import { Button, InfoChip, PageHeader, PageSurface } from "@/shared/ui";
import {
  getCurrentStageMeta,
  getGrandPrixTitle,
  RaceContextPanel,
  StartingGridBoard,
  StartingTireModal,
  TireStrategyPanel
} from "@/pages/_shared/race-weekend";

export function RaceGridPage() {
  const attemptedGridRestoreRef = useRef(false);
  const navigate = useNavigate();
  const [isTireModalOpen, setIsTireModalOpen] = useState(false);
  const selectedTeamId = useSeasonStore((state) => state.selectedTeamId);
  const selectedDriverIds = useSeasonStore((state) => state.selectedDriverIds);
  const cars = useSeasonStore((state) => state.cars);
  const stageProgress = useSeasonStore((state) => state.stageProgress);
  const saveCarSetups = useSeasonStore((state) => state.saveCarSetups);
  const restoreQualifyingResults = useSeasonStore((state) => state.restoreQualifyingResults);
  const isLoading = useSeasonStore((state) => state.isLoading);
  const errorCode = useSeasonStore((state) => state.errorCode);
  const errorMessage = useSeasonStore((state) => state.errorMessage);
  const stage = getCurrentStage();
  const track = getTrack(stage.trackId);
  const selectedTeam = selectedTeamId ? getTeam(selectedTeamId) : getTeam("");
  const qualifyingResults = seasonRepository.getQualifyingResultsByStage(stage.id);
  const raceResults = seasonRepository.getRaceResultsByStage(stage.id);
  const currentProgress = stageProgress.find((progress) => progress.stageId === stage.id);
  const qualifyingStatus = currentProgress?.qualifyingStatus ?? "locked";
  const raceStatus = currentProgress?.raceStatus ?? "locked";
  const hasBlockingError = Boolean(errorMessage && errorCode !== "ENTITY_NOT_FOUND");
  const hasHeavilyDamagedCar = cars.some((car) => car.condition === "heavily-damaged");
  const canLaunchRace =
    qualifyingStatus === "completed" &&
    raceStatus !== "completed" &&
    qualifyingResults.length > 0 &&
    !hasHeavilyDamagedCar &&
    !hasBlockingError;

  useEffect(() => {
    void useSeasonStore
      .getState()
      .refreshSeason()
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (raceStatus === "completed" || raceResults.length > 0) {
      navigate(ROUTES.raceResults, { replace: true });
    }
  }, [navigate, raceResults.length, raceStatus]);

  useEffect(() => {
    if (qualifyingStatus !== "completed" || qualifyingResults.length || isLoading || errorMessage) {
      if (qualifyingStatus !== "completed") {
        attemptedGridRestoreRef.current = false;
      }
      return;
    }

    if (attemptedGridRestoreRef.current) return;

    attemptedGridRestoreRef.current = true;
    void restoreQualifyingResults().catch(() => undefined);
  }, [
    errorMessage,
    isLoading,
    qualifyingResults.length,
    qualifyingStatus,
    restoreQualifyingResults
  ]);

  function handleStartRace() {
    if (!canLaunchRace || isLoading) return;
    setIsTireModalOpen(true);
  }

  async function launchLiveRace(startingTires: Record<string, string>) {
    setIsTireModalOpen(false);
    await saveCarSetups("race", stage.id);

    const params = new URLSearchParams();
    Object.entries(startingTires).forEach(([id, tire]) => {
      params.append(`tire_${id}`, tire);
    });

    navigate(`${ROUTES.liveRace.replace(":id", stage.id)}?${params.toString()}`);
  }

  return (
    <PageSurface className="flex min-h-[calc(100dvh-8rem)] flex-col overflow-hidden">
      <PageHeader
        title={getGrandPrixTitle(track)}
        actions={
          <Button type="button" disabled={!canLaunchRace || isLoading} onClick={handleStartRace}>
            {isLoading ? "Идет гонка..." : "Дать старт гонке"}
          </Button>
        }
        meta={<InfoChip {...getCurrentStageMeta(stage, track)} />}
      />

      {selectedTeamId && cars.length ? <CarConditionPanel /> : null}

      <section className="race-weekend-stage">
        <div className="unified-race-board">
          <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
            <RaceContextPanel
              track={track}
              selectedTeam={selectedTeam}
              selectedDriverIds={selectedDriverIds}
              isResultsView={false}
              gridRows={qualifyingResults}
              raceResults={raceResults}
              weather={stage.weather}
            />

            <div className="flex min-h-0 min-w-0 flex-1 flex-col">
              <TireStrategyPanel strategies={stage.tireStrategies} totalLaps={track.laps} />
              <StartingGridBoard rows={qualifyingResults} selectedTeamId={selectedTeamId} />
            </div>
          </div>
        </div>
      </section>

      <StartingTireModal
        isOpen={isTireModalOpen}
        onClose={() => setIsTireModalOpen(false)}
        onConfirm={launchLiveRace}
        drivers={selectedDriverIds}
        recommendedStartingCompound={stage.recommendedStartingCompound}
      />
    </PageSurface>
  );
}
