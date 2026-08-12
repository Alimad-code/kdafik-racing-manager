import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { Link } from "react-router-dom";
import { getReadableTeamAccent } from "@/shared/lib/teamAccent";
import { cn } from "@/shared/lib/utils";
import { TeamIcon } from "@/shared/ui/TeamIcon";
import { WeatherIcon } from "@/shared/ui/WeatherIcon";
import { resolveLiveDriverName } from "../model/liveDriverName";
import { interpolatePitGameSeconds, legacyPitElapsed } from "../model/pitTiming";
import type { LeaderboardEntry, RaceStatus } from "../model/useLiveRace";
import { LiveTireIndicator } from "./LiveTireIndicator";
import { LIVE_TIRE_COMPOUNDS, liveTireLabels } from "./liveTires";

interface LiveRaceControlBarProps {
  status: RaceStatus;
  entries: LeaderboardEntry[];
  playerDriverIds: string[];
  speedMultiplier: number;
  isFinished: boolean;
  resultsHref: string;
  onCommand: (action: string, carId: string, data?: Record<string, unknown>) => void;
  onSpeedChange: (speed: number) => void;
  onTeamRadioMessage?: (entry: LeaderboardEntry) => void;
}

interface PitCounterState {
  id: string;
  entry: LeaderboardEntry;
  syncedAtMs: number;
  gameTimeRate: number;
  endedAt?: number;
  finalSeconds?: number;
}

const FALLBACK_TEAM_COLOR = "#64748b";
const PIT_COUNTER_HOLD_MS = 3500;
const PIT_COUNTER_LIMIT = 2;
const LIVE_SPEED_OPTIONS = [1, 2, 5] as const;

const weatherLabels: Record<string, string> = {
  none: "Без осадков",
  light: "Лёгкий дождь",
  moderate: "Дождь",
  heavy: "Сильный дождь",
  clear: "Без осадков",
  cloudy: "Без осадков",
  rain: "Дождь",
  mixed: "Дождь",
  dry: "Без осадков",
  "light-rain": "Лёгкий дождь",
  intermediate: "Дождь",
  wet: "Сильный дождь"
};

function formatLiveWeather(value: string) {
  return weatherLabels[value.toLowerCase()] ?? value;
}

function formatTrackTemperature(value: number) {
  return `${value.toFixed(1)}°C`;
}

function formatPitElapsed(seconds: number) {
  return Math.max(0, seconds).toFixed(1);
}

function isInPits(entry: LeaderboardEntry) {
  return entry.status === "IN_PITS";
}

function pitCounterSeconds(counter: PitCounterState, now: number) {
  if (typeof counter.finalSeconds === "number") return counter.finalSeconds;
  const { entry } = counter;
  if (entry.pitElapsedSeconds === null || entry.pitElapsedSeconds === undefined) {
    return legacyPitElapsed(entry.pitServiceElapsedSeconds, entry.pitWaitingSeconds);
  }
  return interpolatePitGameSeconds({
    serverSeconds: entry.pitElapsedSeconds,
    syncedAtMs: counter.syncedAtMs,
    nowMs: now,
    gameTimeRate: counter.gameTimeRate,
    active: entry.status === "IN_PITS"
  });
}

function PitCounter({ counter, now }: { counter: PitCounterState; now: number }) {
  const { entry } = counter;
  const accent = getReadableTeamAccent(entry.teamColor || FALLBACK_TEAM_COLOR);
  const total = pitCounterSeconds(counter, now);

  return (
    <div
      data-testid={`pit-counter-${entry.id}`}
      data-pit-phase={entry.pitPhase ?? "SERVICE"}
      className="w-max min-w-[220px] max-w-[320px] border border-line bg-secondary/95 font-mono uppercase shadow-2xl backdrop-blur"
      style={{ "--team-accent": accent } as CSSProperties}
    >
      <div
        className="flex min-h-8 items-center gap-2 border-b px-2.5"
        style={{ borderColor: "var(--team-accent)" }}
      >
        <span className="w-5 text-base font-black leading-none text-foreground">
          {entry.position}
        </span>
        <TeamIcon className="size-4 shrink-0" color={accent} teamId={entry.teamId} />
        <span className="min-w-0 break-words text-sm font-black leading-tight text-foreground">
          {resolveLiveDriverName(entry.driverId, entry.pilotName)}
        </span>
      </div>
      <div className="flex items-end justify-between gap-3 px-2.5 py-2 font-mono">
        <span className="text-[9px] font-black tracking-[0.12em] text-muted-foreground">
          В ПИТАХ
        </span>
        <span
          data-testid={`pit-game-time-${entry.id}`}
          className="text-2xl font-black leading-none tracking-tight text-foreground"
        >
          {formatPitElapsed(total)} с
        </span>
      </div>
    </div>
  );
}

interface PlayerPitControlProps {
  driverId: string;
  entry?: LeaderboardEntry;
  isMenuOpen: boolean;
  slotIndex: number;
  onMenuToggle: () => void;
  onPitStop: (carId: string, compound: string) => void;
}

function PlayerPitControl({
  driverId,
  entry,
  isMenuOpen,
  slotIndex,
  onMenuToggle,
  onPitStop
}: PlayerPitControlProps) {
  const accent = getReadableTeamAccent(entry?.teamColor || FALLBACK_TEAM_COLOR);
  const canBox = entry?.status === "RACING";
  const tireCondition = Math.round(entry?.tireCondition ?? 0);
  const driverName = resolveLiveDriverName(driverId, entry?.pilotName);

  return (
    <div
      data-testid="player-driver-control"
      data-driver-id={driverId}
      className="relative flex min-h-[72px] min-w-0 items-center gap-2 border-r border-line bg-card/80 px-2 py-2 last:border-r-0"
      style={{ "--team-accent": accent } as CSSProperties}
    >
      <span
        aria-hidden="true"
        className="absolute inset-x-0 top-0 h-px"
        style={{ backgroundColor: "var(--team-accent)" }}
      />

      <TeamIcon
        className="size-4 shrink-0"
        color={accent}
        teamId={entry?.teamId ?? "unknown-team"}
      />

      <div className="min-w-0 flex-1 font-mono uppercase">
        <p className="flex min-w-0 items-baseline gap-2">
          <span className="shrink-0 text-[8px] font-black tracking-[0.18em] text-muted-foreground">
            Пилот {slotIndex + 1}
          </span>
          <strong className="truncate text-[13px] font-black leading-none text-foreground">
            {driverName}
          </strong>
        </p>
        <div className="mt-2 flex min-w-0 items-center gap-2 text-[9px] font-black tracking-[0.08em] text-muted-foreground">
          <LiveTireIndicator compound={entry?.tireCompound} />
          <span className="truncate">
            {entry ? `Износ шин ${tireCondition}%` : "Ожидание телеметрии"}
          </span>
        </div>
      </div>

      <button
        type="button"
        aria-expanded={isMenuOpen}
        disabled={!canBox}
        onClick={onMenuToggle}
        className={cn(
          "shrink-0 border px-2 py-2 font-mono text-[9px] font-black uppercase tracking-[0.1em] transition",
          canBox
            ? "border-primary/70 bg-primary/15 text-primary hover:bg-primary hover:text-primary-foreground"
            : "cursor-not-allowed border-line bg-muted/30 text-muted-foreground"
        )}
      >
        Пит-стоп
      </button>

      {isMenuOpen && entry ? (
        <div className="absolute inset-x-2 top-[calc(100%-1px)] z-[60] grid grid-cols-5 gap-1 border border-line bg-secondary/98 p-1 shadow-2xl backdrop-blur">
          {LIVE_TIRE_COMPOUNDS.map((compound) => (
            <button
              key={compound}
              type="button"
              onClick={() => onPitStop(entry.id, compound)}
              className="min-w-0 border border-line bg-surface px-1 py-2 font-mono text-[8px] font-black uppercase text-muted-foreground transition hover:border-primary hover:text-primary"
            >
              {liveTireLabels[compound]}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function LiveRaceControlBar({
  status,
  entries,
  playerDriverIds,
  speedMultiplier,
  isFinished,
  resultsHref,
  onCommand,
  onSpeedChange,
  onTeamRadioMessage
}: LiveRaceControlBarProps) {
  const [selectedCarForPit, setSelectedCarForPit] = useState<string | null>(null);
  const [pitCounters, setPitCounters] = useState<PitCounterState[]>([]);
  const [now, setNow] = useState(Date.now());
  const entriesByDriverId = useMemo(
    () => new Map(entries.map((entry) => [entry.driverId, entry])),
    [entries]
  );
  const playerEntries = useMemo(
    () =>
      playerDriverIds
        .map((driverId) => entriesByDriverId.get(driverId))
        .filter((entry): entry is LeaderboardEntry => entry !== undefined),
    [entriesByDriverId, playerDriverIds]
  );

  useEffect(() => {
    const currentTime = Date.now();
    const activePitEntries = [
      ...playerEntries.filter(isInPits),
      ...entries.filter((entry) => isInPits(entry) && !playerDriverIds.includes(entry.driverId))
    ];
    const activePitIds = new Set(activePitEntries.map((entry) => entry.id));

    setPitCounters((current) => {
      const updated = current
        .map((counter) => {
          const liveEntry = entries.find((entry) => entry.id === counter.id);

          return {
            ...counter,
            entry: liveEntry ?? counter.entry,
            syncedAtMs: activePitIds.has(counter.id) ? currentTime : counter.syncedAtMs,
            gameTimeRate: activePitIds.has(counter.id) ? status.gameTimeRate : counter.gameTimeRate,
            endedAt: activePitIds.has(counter.id)
              ? undefined
              : !counter.endedAt
                ? currentTime
                : counter.endedAt,
            finalSeconds: activePitIds.has(counter.id)
              ? undefined
              : !counter.endedAt
                ? typeof liveEntry?.pitElapsedSeconds === "number"
                  ? liveEntry.pitElapsedSeconds
                  : pitCounterSeconds(counter, currentTime)
                : counter.finalSeconds
          };
        })
        .filter(
          (counter) => !counter.endedAt || currentTime - counter.endedAt <= PIT_COUNTER_HOLD_MS
        );

      const visibleIds = new Set(updated.map((counter) => counter.id));
      const availableSlots = PIT_COUNTER_LIMIT - updated.length;
      const nextCounters = activePitEntries
        .filter((entry) => !visibleIds.has(entry.id))
        .slice(0, Math.max(0, availableSlots))
        .map((entry) => ({
          id: entry.id,
          entry,
          syncedAtMs: currentTime,
          gameTimeRate: status.gameTimeRate
        }));

      return [...updated, ...nextCounters];
    });
  }, [entries, playerDriverIds, playerEntries, status.gameTimeRate]);

  useEffect(() => {
    if (!pitCounters.length) return;
    const timer = window.setInterval(() => setNow(Date.now()), 100);
    return () => window.clearInterval(timer);
  }, [pitCounters.length]);

  useEffect(() => {
    setPitCounters((current) => {
      const filtered = current.filter(
        (counter) => !counter.endedAt || now - counter.endedAt <= PIT_COUNTER_HOLD_MS
      );
      return filtered.length === current.length ? current : filtered;
    });
  }, [now]);

  function handlePitStop(carId: string, compound: string) {
    const entry = entries.find((item) => item.id === carId);
    if (entry) onTeamRadioMessage?.(entry);
    onCommand("BOX_THIS_LAP", carId, { target_tires: compound });
    setSelectedCarForPit(null);
  }

  return (
    <>
      <div
        data-testid="live-race-control-bar"
        className="relative z-30 grid shrink-0 grid-cols-[360px_repeat(2,minmax(0,1fr))] border-b border-line bg-background/70 shadow-insetLine"
      >
        <div
          data-testid="live-global-telemetry"
          className="grid min-h-[72px] grid-cols-[72px_minmax(0,1fr)_104px] border-r border-line font-mono uppercase"
        >
          <div className="flex min-w-0 flex-col justify-center border-r border-line/70 px-3">
            <span className="text-[8px] font-black tracking-[0.2em] text-muted-foreground">
              Круг
            </span>
            <strong className="mt-2 whitespace-nowrap text-lg font-black leading-none text-foreground">
              {status.currentLap} / {status.totalLaps}
            </strong>
          </div>
          <div className="grid min-w-0 grid-rows-2">
            <div className="flex min-w-0 items-center justify-between gap-2 border-b border-line/70 px-3">
              <span className="shrink-0 text-[8px] font-black tracking-[0.18em] text-muted-foreground">
                Осадки
              </span>
              <strong className="flex min-w-0 items-center justify-end gap-1.5 text-[10px] font-black leading-none text-foreground">
                <WeatherIcon className="size-3.5" value={status.precipitation} />
                <span data-testid="live-weather-label" className="truncate">
                  {formatLiveWeather(status.precipitation)}
                </span>
              </strong>
            </div>
            <div className="flex min-w-0 items-center justify-between gap-2 px-3">
              <span className="shrink-0 text-[8px] font-black tracking-[0.18em] text-muted-foreground">
                Трасса
              </span>
              <strong
                data-testid="live-track-temperature"
                className="whitespace-nowrap text-sm font-black leading-none text-foreground"
              >
                {formatTrackTemperature(status.trackTemp)}
              </strong>
            </div>
          </div>
          <div
            className="flex min-w-0 flex-col justify-center border-l border-line/70 px-2"
            data-testid="live-speed-control"
          >
            {isFinished ? (
              <Link
                to={resultsHref}
                className="border border-primary/70 bg-primary/15 px-1 py-2 text-center text-[8px] font-black uppercase tracking-[0.08em] text-primary transition hover:bg-primary hover:text-primary-foreground"
              >
                Открыть итоги
              </Link>
            ) : (
              <>
                <span className="text-[8px] font-black tracking-[0.18em] text-muted-foreground">
                  Темп
                </span>
                <div className="mt-1 flex border border-line bg-secondary p-0.5 shadow-insetLine">
                  {LIVE_SPEED_OPTIONS.map((speed) => (
                    <button
                      key={speed}
                      type="button"
                      aria-label={`Скорость гонки ${speed}X`}
                      aria-pressed={speedMultiplier === speed}
                      onClick={() => onSpeedChange(speed)}
                      className={cn(
                        "min-w-0 flex-1 px-1 py-1 text-[9px] font-black transition-colors",
                        speedMultiplier === speed
                          ? "bg-primary text-primary-foreground"
                          : "text-muted-foreground hover:bg-muted hover:text-foreground"
                      )}
                    >
                      {speed}X
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>

        {playerDriverIds.slice(0, 2).map((driverId, slotIndex) => {
          const entry = entriesByDriverId.get(driverId);
          return (
            <PlayerPitControl
              key={driverId}
              driverId={driverId}
              entry={entry}
              isMenuOpen={Boolean(entry && selectedCarForPit === entry.id)}
              slotIndex={slotIndex}
              onMenuToggle={() =>
                entry && setSelectedCarForPit((current) => (current === entry.id ? null : entry.id))
              }
              onPitStop={handlePitStop}
            />
          );
        })}
      </div>

      {pitCounters.length ? (
        <div className="absolute bottom-5 right-5 z-40 flex flex-col-reverse items-end gap-0">
          {pitCounters.map((counter) => (
            <PitCounter key={counter.id} counter={counter} now={now} />
          ))}
        </div>
      ) : null}
    </>
  );
}
