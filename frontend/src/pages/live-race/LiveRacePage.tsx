import { useEffect, useRef, useMemo, useState } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { ROUTES } from "@/shared/constants/routes";
import { PageSurface, PageHeader } from "@/shared/ui";
import { seasonRepository } from "@/features/season/api/seasonDataSource";
import { getTeam, getTrack, getCurrentStage } from "@/features/season/lib/seasonViewData";
import { getGrandPrixTitle } from "@/pages/_shared/race-weekend";
import { useSeasonStore } from "@/features/season/model/useSeasonStore";
import { cn } from "@/shared/lib/utils";
import { LiveRaceMap } from "./ui/LiveRaceMap";
import { LiveLeaderboard } from "./ui/LiveLeaderboard";
import { LiveRaceControlBar } from "./ui/LiveRaceControlBar";
import { useLiveRace } from "./model/useLiveRace";
import { LiveRadio } from "./ui/LiveRadio";
import { LiveBroadcastOverlay } from "./ui/LiveBroadcastOverlay";
import { resolveLiveDriverName } from "./model/liveDriverName";
import type { CarPosition, LeaderboardEntry } from "./model/useLiveRace";

// Fallback simple oval path if none provided
const FALLBACK_SVG_PATH = "M 200,500 A 300,150 0 1,1 800,500 A 300,150 0 1,1 200,500";
const GRID_FRONT_OFFSET_METERS = 6;
const GRID_ROW_SPACING_METERS = 12;
const GRID_SLOT_STAGGER_METERS = 6;
const GRID_LANE_OFFSET_METERS = 4.5;

function RaceStartLights({ step }: { step: number }) {
  const isGreen = step >= 5;
  const redCount = Math.min(5, step + 1);

  return (
    <div className="absolute inset-0 z-20 flex items-center justify-center bg-background/45 backdrop-blur-[1px]">
      <div className="flex items-center gap-3 border border-line bg-secondary px-5 py-4 shadow-2xl">
        {Array.from({ length: 5 }).map((_, index) => (
          <span
            key={index}
            className={cn(
              "size-8 rounded-full border border-line shadow-[0_0_18px_rgba(0,0,0,0.4)] transition-colors",
              isGreen
                ? "bg-success shadow-[0_0_26px_rgba(34,197,94,0.8)]"
                : index < redCount
                  ? "bg-primary shadow-[0_0_24px_rgba(109,40,217,0.75)]"
                  : "bg-muted"
            )}
          />
        ))}
      </div>
    </div>
  );
}

export function LiveRacePage() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const stageId = id || getCurrentStage().id;
  const stage =
    seasonRepository.getStages().find((item) => item.id === stageId) ?? getCurrentStage();
  const track = getTrack(stage.trackId);
  const trackPath = track.svgPath || FALLBACK_SVG_PATH;
  const selectedDriverIds = useSeasonStore((state) => state.selectedDriverIds);
  const qualifyingResults = seasonRepository.getQualifyingResultsByStage(stage.id);
  const [startPhase, setStartPhase] = useState<"lights" | "live">("lights");
  const [lightsStep, setLightsStep] = useState(0);

  const startingTiresJson = JSON.stringify(
    Object.fromEntries(
      Array.from(searchParams.entries())
        .filter(([key]) => key.startsWith("tire_"))
        .map(([key, value]) => [key.replace("tire_", ""), value])
    )
  );

  const startingTires = useMemo(() => {
    return JSON.parse(startingTiresJson) as Record<string, string>;
  }, [startingTiresJson]);

  const {
    raceStatus,
    leaderboard,
    carPositions,
    radioMessage,
    timingCues,
    broadcastEvent,
    sendCommand,
    showRadioMessage
  } = useLiveRace(stageId, startingTires, startPhase === "live");
  const refreshSeason = useSeasonStore((state) => state.refreshSeason);
  const restoreRaceResults = useSeasonStore((state) => state.restoreRaceResults);

  const [currentSpeed, setCurrentSpeed] = useState(1);

  const gridPreviewCars = useMemo<CarPosition[]>(() => {
    const circuitLengthMeters = Math.max(1, track.lengthKm * 1000);

    return [...qualifyingResults]
      .sort((left, right) => left.position - right.position)
      .map((row) => {
        const rowIndex = Math.floor((row.position - 1) / 2);
        const lane = (row.position - 1) % 2;
        const distance = -(
          GRID_FRONT_OFFSET_METERS +
          rowIndex * GRID_ROW_SPACING_METERS +
          lane * GRID_SLOT_STAGGER_METERS
        );

        return {
          driver_id: row.driverId,
          team_id: row.teamId,
          team_color: getTeam(row.teamId).color,
          lap_percentage: Math.max(0, Math.min(1, 1 + distance / circuitLengthMeters)),
          distance_meters: distance,
          position: row.position,
          grid_position: row.position,
          grid_row: rowIndex + 1,
          grid_lane: lane,
          lane_offset_meters: lane === 0 ? -GRID_LANE_OFFSET_METERS : GRID_LANE_OFFSET_METERS,
          status: "RACING"
        };
      });
  }, [qualifyingResults, track.lengthKm]);

  const setSpeed = (speed: number) => {
    setCurrentSpeed(speed);
    sendCommand("SET_SPEED", "", { multiplier: speed });
  };

  function emitTeamRadioMessage(entry: LeaderboardEntry) {
    showRadioMessage({
      id: `team-radio-${entry.id}-${Date.now()}`,
      driverId: entry.driverId,
      pilotName: resolveLiveDriverName(entry.driverId, entry.pilotName),
      teamId: entry.teamId,
      teamColor: entry.teamColor,
      source: "team",
      text: "box, box",
      timestamp: Date.now()
    });
  }

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const restoredRaceRef = useRef(false);

  useEffect(() => {
    if (startPhase !== "lights") return;

    const timer = window.setTimeout(() => {
      if (lightsStep >= 5) {
        setStartPhase("live");
        return;
      }
      setLightsStep((value) => value + 1);
    }, 350);

    return () => window.clearTimeout(timer);
  }, [lightsStep, startPhase]);

  // Auto-redirect or show view results when finished
  useEffect(() => {
    if (raceStatus.isFinished && !restoredRaceRef.current) {
      restoredRaceRef.current = true;
      const restoreAndNavigate = async () => {
        try {
          await restoreRaceResults(stageId, { waitForAutosave: true });
          await refreshSeason();

          setTimeout(() => {
            navigate(ROUTES.raceResults);
          }, 2000);
        } catch (err) {
          console.error("Failed to restore live race results:", err);
          navigate(ROUTES.raceResults);
        }
      };

      timerRef.current = setTimeout(restoreAndNavigate, 5000);
    }
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [raceStatus.isFinished, navigate, refreshSeason, restoreRaceResults, stageId]);

  return (
    <PageSurface className="relative flex h-[calc(100dvh-9.25rem)] min-h-[560px] flex-col overflow-hidden">
      <PageHeader title={getGrandPrixTitle(track)} />

      <section
        data-testid="live-race-panel"
        className="race-panel relative grid min-h-0 flex-1 overflow-hidden bg-surface lg:grid-cols-[270px_minmax(0,1fr)]"
      >
        <aside className="flex min-h-0 flex-col border-r border-line bg-surface py-1">
          <LiveLeaderboard
            status={raceStatus}
            entries={leaderboard}
            timingCues={timingCues}
            playerDriverIds={selectedDriverIds}
          />
        </aside>

        <div className="flex min-h-0 min-w-0 flex-col bg-surface">
          <LiveRaceControlBar
            status={raceStatus}
            entries={leaderboard}
            playerDriverIds={selectedDriverIds}
            speedMultiplier={currentSpeed}
            isFinished={raceStatus.isFinished}
            resultsHref={ROUTES.raceResults}
            onCommand={sendCommand}
            onSpeedChange={setSpeed}
            onTeamRadioMessage={emitTeamRadioMessage}
          />

          <div
            data-testid="live-race-map-stage"
            className="relative flex min-h-0 flex-1 items-center justify-center overflow-hidden bg-surface"
          >
            <LiveBroadcastOverlay event={broadcastEvent} />
            <LiveRaceMap
              svgPath={trackPath}
              cars={startPhase === "live" ? carPositions : gridPreviewCars}
              playerDriverIds={selectedDriverIds}
              speedMultiplier={currentSpeed}
              trackWetness={raceStatus.trackWetness}
            />

            {startPhase === "lights" && <RaceStartLights step={lightsStep} />}
            <LiveRadio message={radioMessage} />
          </div>
        </div>
      </section>
    </PageSurface>
  );
}
