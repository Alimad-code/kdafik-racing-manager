import { useState, useEffect, useRef } from "react";
import { apiRequest } from "@/features/season/api/apiClient";
import { useSeasonStore } from "@/features/season/model/useSeasonStore";
import { mergeTimingCueStore, type TimingCueStore } from "./liveTiming";
import {
  advanceBroadcastQueue,
  BROADCAST_DURATION_MS,
  createBroadcastQueue,
  enqueueBroadcastEvents,
  type BroadcastQueueState
} from "./liveBroadcast";
import {
  createLiveNotificationState,
  expireRadioMessage,
  RADIO_DURATION_MS,
  replaceRadioMessage
} from "./liveNotifications";

export interface RaceStatus {
  currentLap: number;
  totalLaps: number;
  precipitation: string;
  isFinished: boolean;
  trackTemp: number;
  rainIntensity: number;
  trackWetness: number;
  gameTimeRate: number;
}

export interface CarPosition {
  driver_id: string;
  pilot_name?: string;
  code?: string;
  team_id: string;
  team_color: string;
  lap_percentage: number;
  distance_meters?: number;
  position?: number;
  grid_position?: number;
  grid_row?: number;
  grid_lane?: number;
  lane_offset_meters?: number;
  is_attacking?: boolean;
  attack_target_id?: string | null;
  duel_id?: string | null;
  duel_phase?: string | null;
  duel_role?: string | null;
  status?: string;
}

export interface LeaderboardEntry {
  id: string; // The unique car UUID
  driverId: string; // The driver ID (e.g. driver-novak)
  position: number;
  pilotName: string;
  teamId: string;
  teamColor: string;
  gap: string;
  lap: number;
  tireCompound?: string;
  tireCondition?: number;
  gridPosition?: number;
  gridRow?: number;
  gridLane?: number;
  laneOffsetMeters?: number;
  speed?: number;
  gapToAheadMs?: number | null;
  gapToLeaderMs?: number | null;
  isAttacking?: boolean;
  attackTargetId?: string | null;
  duelId?: string | null;
  duelPhase?: string | null;
  duelRole?: string | null;
  pitPhase?: string | null;
  pitServiceDurationSeconds?: number | null;
  pitServiceElapsedSeconds?: number;
  pitWaitingSeconds?: number;
  pitElapsedSeconds?: number | null;
  status: string;
  lastLapTimeMs?: number | null;
  lastLapNumber?: number | null;
  personalBestLapTimeMs?: number | null;
  personalBestLapNumber?: number | null;
  maxSpeedKph?: number;
  isFastestLap?: boolean;
}

export interface TimingCue {
  id: string;
  type: string;
  carId?: string;
  driverId?: string;
  lapNumber?: number;
  lapTimeMs?: number;
  durationMs: number;
}

export interface BroadcastEvent {
  id: string;
  type: "FASTEST_LAP" | "LEADER_CHANGED" | "FINAL_LAP_STARTED";
  carId: string;
  driverId: string;
  pilotName: string;
  pilotCode: string;
  teamId: string;
  teamColor: string;
  lapTimeMs: number | null;
  lapNumber: number | null;
  occurredAtRaceTime: number;
}

export type RadioMessageSource = "driver" | "team";

export interface RadioMessage {
  id: string;
  driverId: string;
  pilotName: string;
  teamId: string;
  teamColor: string;
  source: RadioMessageSource;
  text: string;
  timestamp: number;
}

type RawLiveCar = Record<string, unknown> & {
  tires?: Record<string, unknown>;
};

type NormalizedLiveCar = {
  id: string;
  driverId: string;
  pilotName: string;
  teamId: string;
  teamColor: string;
  position: number;
  lap: number;
  lapProgress: number;
  distanceMeters?: number;
  gap: string;
  gridPosition?: number;
  gridRow?: number;
  gridLane?: number;
  laneOffsetMeters?: number;
  speed?: number;
  gapToAheadMs?: number | null;
  gapToLeaderMs?: number | null;
  isAttacking: boolean;
  attackTargetId?: string | null;
  duelId?: string | null;
  duelPhase?: string | null;
  duelRole?: string | null;
  pitPhase?: string | null;
  pitServiceDurationSeconds?: number | null;
  pitServiceElapsedSeconds: number;
  pitWaitingSeconds: number;
  pitElapsedSeconds?: number | null;
  status: string;
  lastLapTimeMs?: number | null;
  lastLapNumber?: number | null;
  personalBestLapTimeMs?: number | null;
  personalBestLapNumber?: number | null;
  maxSpeedKph: number;
  isFastestLap: boolean;
  tires?: {
    compound: string;
    condition: number;
  };
};

type NormalizedLivePayload = {
  type: string;
  totalLaps?: number;
  gameTimeRate?: number;
  cars: NormalizedLiveCar[];
  notification?: {
    carId: string;
    driverId: string;
    pilotName: string;
    teamId: string;
    teamColor: string;
    source: RadioMessageSource;
    message: string;
  } | null;
  weather?: {
    precipitation: string;
    trackTemp: number;
    rainIntensity: number;
    trackWetness: number;
  };
  raceTiming?: {
    fastestLapCarId?: string | null;
    fastestLapDriverId?: string | null;
    fastestLapTimeMs?: number | null;
    fastestLapNumber?: number | null;
  };
  timingCues: TimingCue[];
  broadcastEvents: BroadcastEvent[];
};

function readString(value: unknown, fallback = "") {
  return typeof value === "string" ? value : fallback;
}

function readNumber(value: unknown, fallback = 0) {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function normalizeLiveCar(rawCar: RawLiveCar): NormalizedLiveCar {
  const tires = rawCar.tires;

  return {
    id: readString(rawCar.id),
    driverId: readString(rawCar.driverId ?? rawCar.driver_id),
    pilotName: readString(rawCar.pilotName ?? rawCar.pilot_name ?? rawCar.driverCode, "DRV"),
    teamId: readString(rawCar.teamId ?? rawCar.team_id),
    teamColor: readString(rawCar.teamColor ?? rawCar.team_color, "#64748b"),
    position: readNumber(rawCar.position, 0),
    lap: readNumber(rawCar.lap, 1),
    lapProgress: Math.max(
      0,
      Math.min(1, readNumber(rawCar.lapProgress ?? rawCar.lap_progress ?? rawCar.lapPercentage, 0))
    ),
    distanceMeters:
      typeof (rawCar.distanceMeters ?? rawCar.distance_meters) === "number"
        ? readNumber(rawCar.distanceMeters ?? rawCar.distance_meters)
        : undefined,
    gap: readString(rawCar.gap, "-"),
    gridPosition:
      typeof (rawCar.gridPosition ?? rawCar.grid_position) === "number"
        ? readNumber(rawCar.gridPosition ?? rawCar.grid_position)
        : undefined,
    gridRow:
      typeof (rawCar.gridRow ?? rawCar.grid_row) === "number"
        ? readNumber(rawCar.gridRow ?? rawCar.grid_row)
        : undefined,
    gridLane:
      typeof (rawCar.gridLane ?? rawCar.grid_lane) === "number"
        ? readNumber(rawCar.gridLane ?? rawCar.grid_lane)
        : undefined,
    laneOffsetMeters:
      typeof (rawCar.laneOffsetMeters ?? rawCar.lane_offset_meters) === "number"
        ? readNumber(rawCar.laneOffsetMeters ?? rawCar.lane_offset_meters)
        : undefined,
    speed: typeof rawCar.speed === "number" ? readNumber(rawCar.speed) : undefined,
    gapToAheadMs:
      typeof (rawCar.gapToAheadMs ?? rawCar.gap_to_ahead_ms) === "number"
        ? readNumber(rawCar.gapToAheadMs ?? rawCar.gap_to_ahead_ms)
        : null,
    gapToLeaderMs:
      typeof (rawCar.gapToLeaderMs ?? rawCar.gap_to_leader_ms) === "number"
        ? readNumber(rawCar.gapToLeaderMs ?? rawCar.gap_to_leader_ms)
        : null,
    isAttacking: Boolean(rawCar.isAttacking ?? rawCar.is_attacking),
    attackTargetId:
      typeof (rawCar.attackTargetId ?? rawCar.attack_target_id) === "string"
        ? readString(rawCar.attackTargetId ?? rawCar.attack_target_id)
        : null,
    duelId:
      typeof (rawCar.duelId ?? rawCar.duel_id) === "string"
        ? readString(rawCar.duelId ?? rawCar.duel_id)
        : null,
    duelPhase:
      typeof (rawCar.duelPhase ?? rawCar.duel_phase) === "string"
        ? readString(rawCar.duelPhase ?? rawCar.duel_phase).toUpperCase()
        : null,
    duelRole:
      typeof (rawCar.duelRole ?? rawCar.duel_role) === "string"
        ? readString(rawCar.duelRole ?? rawCar.duel_role).toUpperCase()
        : null,
    pitPhase:
      typeof (rawCar.pitPhase ?? rawCar.pit_phase) === "string"
        ? readString(rawCar.pitPhase ?? rawCar.pit_phase).toUpperCase()
        : null,
    pitServiceDurationSeconds:
      typeof (rawCar.pitServiceDurationSeconds ?? rawCar.pit_service_duration_seconds) === "number"
        ? readNumber(rawCar.pitServiceDurationSeconds ?? rawCar.pit_service_duration_seconds)
        : null,
    pitServiceElapsedSeconds: readNumber(
      rawCar.pitServiceElapsedSeconds ?? rawCar.pit_service_elapsed_seconds,
      0
    ),
    pitWaitingSeconds: readNumber(rawCar.pitWaitingSeconds ?? rawCar.pit_waiting_seconds, 0),
    pitElapsedSeconds:
      typeof (rawCar.pitElapsedSeconds ?? rawCar.pit_elapsed_seconds) === "number"
        ? readNumber(rawCar.pitElapsedSeconds ?? rawCar.pit_elapsed_seconds)
        : null,
    status: readString(rawCar.status, "RACING").toUpperCase(),
    lastLapTimeMs:
      typeof (rawCar.lastLapTimeMs ?? rawCar.last_lap_time_ms) === "number"
        ? readNumber(rawCar.lastLapTimeMs ?? rawCar.last_lap_time_ms)
        : null,
    lastLapNumber:
      typeof (rawCar.lastLapNumber ?? rawCar.last_lap_number) === "number"
        ? readNumber(rawCar.lastLapNumber ?? rawCar.last_lap_number)
        : null,
    personalBestLapTimeMs:
      typeof (rawCar.personalBestLapTimeMs ?? rawCar.personal_best_lap_time_ms) === "number"
        ? readNumber(rawCar.personalBestLapTimeMs ?? rawCar.personal_best_lap_time_ms)
        : null,
    personalBestLapNumber:
      typeof (rawCar.personalBestLapNumber ?? rawCar.personal_best_lap_number) === "number"
        ? readNumber(rawCar.personalBestLapNumber ?? rawCar.personal_best_lap_number)
        : null,
    maxSpeedKph: readNumber(rawCar.maxSpeedKph ?? rawCar.max_speed_kph, 0),
    isFastestLap: Boolean(rawCar.isFastestLap ?? rawCar.is_fastest_lap),
    tires: tires
      ? {
          compound: readString(tires.compound, "Medium"),
          condition: readNumber(tires.condition, 100)
        }
      : undefined
  };
}

export function normalizeLivePayload(rawData: unknown): NormalizedLivePayload | null {
  if (!rawData || typeof rawData !== "object") {
    return null;
  }

  const payload = rawData as Record<string, unknown>;
  const rawCars = Array.isArray(payload.cars) ? payload.cars : [];
  const weather =
    payload.weather && typeof payload.weather === "object"
      ? (payload.weather as Record<string, unknown>)
      : undefined;
  const rawNotification =
    payload.notification && typeof payload.notification === "object"
      ? (payload.notification as Record<string, unknown>)
      : null;
  const rawTiming = payload.raceTiming ?? payload.race_timing;
  const rawCues = payload.timingCues ?? payload.timing_cues;
  const rawBroadcastEvents = payload.broadcastEvents ?? payload.broadcast_events;

  return {
    type: readString(payload.type).toUpperCase(),
    totalLaps:
      typeof (payload.totalLaps ?? payload.total_laps) === "number"
        ? readNumber(payload.totalLaps ?? payload.total_laps)
        : undefined,
    gameTimeRate:
      typeof (payload.gameTimeRate ?? payload.game_time_rate) === "number"
        ? readNumber(payload.gameTimeRate ?? payload.game_time_rate)
        : 0,
    cars: rawCars.map((car) => normalizeLiveCar(car as RawLiveCar)).filter((car) => car.id),
    notification: rawNotification
      ? {
          carId: readString(rawNotification.carId ?? rawNotification.car_id),
          driverId: readString(rawNotification.driverId ?? rawNotification.driver_id),
          pilotName: readString(rawNotification.pilotName ?? rawNotification.pilot_name, "DRV"),
          teamId: readString(rawNotification.teamId ?? rawNotification.team_id),
          teamColor: readString(rawNotification.teamColor ?? rawNotification.team_color, "#64748b"),
          source:
            readString(rawNotification.source ?? rawNotification.type, "driver").toLowerCase() ===
            "team"
              ? "team"
              : "driver",
          message: readString(rawNotification.message)
        }
      : null,
    weather: weather
      ? (() => {
          const rainIntensity = readNumber(weather.rainIntensity, 0);
          return {
            precipitation: readString(weather.precipitation, "none"),
            trackTemp: readNumber(weather.trackTemp, 30),
            rainIntensity,
            trackWetness: Math.max(0, Math.min(1, readNumber(weather.trackWetness, 0)))
          };
        })()
      : undefined,
    raceTiming:
      rawTiming && typeof rawTiming === "object"
        ? (() => {
            const item = rawTiming as Record<string, unknown>;
            return {
              fastestLapCarId:
                typeof (item.fastestLapCarId ?? item.fastest_lap_car_id) === "string"
                  ? readString(item.fastestLapCarId ?? item.fastest_lap_car_id)
                  : null,
              fastestLapDriverId:
                typeof (item.fastestLapDriverId ?? item.fastest_lap_driver_id) === "string"
                  ? readString(item.fastestLapDriverId ?? item.fastest_lap_driver_id)
                  : null,
              fastestLapTimeMs:
                typeof (item.fastestLapTimeMs ?? item.fastest_lap_time_ms) === "number"
                  ? readNumber(item.fastestLapTimeMs ?? item.fastest_lap_time_ms)
                  : null,
              fastestLapNumber:
                typeof (item.fastestLapNumber ?? item.fastest_lap_number) === "number"
                  ? readNumber(item.fastestLapNumber ?? item.fastest_lap_number)
                  : null
            };
          })()
        : undefined,
    timingCues: Array.isArray(rawCues)
      ? rawCues
          .map((cue) => {
            const item = cue as Record<string, unknown>;
            return {
              id: readString(item.id),
              type: readString(item.type).toUpperCase(),
              carId: readString(item.carId ?? item.car_id) || undefined,
              driverId: readString(item.driverId ?? item.driver_id) || undefined,
              lapNumber:
                typeof (item.lapNumber ?? item.lap_number) === "number"
                  ? readNumber(item.lapNumber ?? item.lap_number)
                  : undefined,
              lapTimeMs:
                typeof (item.lapTimeMs ?? item.lap_time_ms) === "number"
                  ? readNumber(item.lapTimeMs ?? item.lap_time_ms)
                  : undefined,
              durationMs: readNumber(item.durationMs ?? item.duration_ms, 0)
            };
          })
          .filter((cue) => cue.id)
      : [],
    broadcastEvents: Array.isArray(rawBroadcastEvents)
      ? rawBroadcastEvents
          .map((event) => {
            const item = event as Record<string, unknown>;
            const type = readString(item.type).toUpperCase();
            const carId = readString(item.carId ?? item.car_id);
            const driverId = readString(item.driverId ?? item.driver_id);
            const lapNumber =
              typeof (item.lapNumber ?? item.lap_number) === "number"
                ? readNumber(item.lapNumber ?? item.lap_number)
                : null;
            const occurredAtRaceTime = readNumber(
              item.occurredAtRaceTime ?? item.occurred_at_race_time
            );
            return {
              id:
                readString(item.id) || `${type}:${carId}:${lapNumber ?? ""}:${occurredAtRaceTime}`,
              type,
              carId,
              driverId,
              pilotName: readString(item.pilotName ?? item.pilot_name),
              pilotCode: readString(item.pilotCode ?? item.pilot_code),
              teamId: readString(item.teamId ?? item.team_id),
              teamColor: readString(item.teamColor ?? item.team_color),
              lapTimeMs:
                typeof (item.lapTimeMs ?? item.lap_time_ms) === "number"
                  ? readNumber(item.lapTimeMs ?? item.lap_time_ms)
                  : null,
              lapNumber,
              occurredAtRaceTime
            };
          })
          .filter(
            (event): event is BroadcastEvent =>
              Boolean(event.id) &&
              (event.type === "FASTEST_LAP" ||
                event.type === "LEADER_CHANGED" ||
                event.type === "FINAL_LAP_STARTED")
          )
      : []
  };
}

function isFinishedPayload(type: string, cars: NormalizedLiveCar[]) {
  if (type.includes("FINISH") || type.includes("COMPLETE") || type.includes("END")) {
    return true;
  }

  return cars.length > 0 && cars.every((car) => car.status === "FINISHED" || car.status === "DNF");
}

function isBackendTeamPitCall(notification: NonNullable<NormalizedLivePayload["notification"]>) {
  const normalizedMessage = notification.message
    .toLowerCase()
    .replace(/[,\s]+/g, " ")
    .trim();

  return notification.source === "team" && normalizedMessage === "box box";
}

export function useLiveRace(
  stageId: string,
  startingTires?: Record<string, string>,
  enabled = true
) {
  const [raceStatus, setRaceStatus] = useState<RaceStatus>({
    currentLap: 1,
    totalLaps: 1,
    precipitation: "none",
    isFinished: false,
    trackTemp: 30,
    rainIntensity: 0,
    trackWetness: 0,
    gameTimeRate: 0
  });
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [carPositions, setCarPositions] = useState<CarPosition[]>([]);
  const [radioMessage, setRadioMessage] = useState<RadioMessage | null>(null);
  const [timingCueStore, setTimingCueStore] = useState<TimingCueStore>({
    active: [],
    recentIds: []
  });
  const [broadcastQueue, setBroadcastQueue] = useState<BroadcastQueueState>(createBroadcastQueue);
  const [isConnected, setIsConnected] = useState(false);
  const seasonId = useSeasonStore((state) => state.activeSeasonId);
  const wsRef = useRef<WebSocket | null>(null);
  const broadcastSeenIdsRef = useRef(new Set<string>());

  const clearTransientNotifications = () => {
    const empty = createLiveNotificationState();
    setRadioMessage(empty.radioMessage);
    setBroadcastQueue(empty.broadcastQueue);
    broadcastSeenIdsRef.current.clear();
  };

  const showRadioMessage = (message: RadioMessage) => {
    setRadioMessage((current) => replaceRadioMessage(current, message));
  };

  useEffect(() => {
    if (!enabled) {
      setIsConnected(false);
      clearTransientNotifications();
      return;
    }
    if (!seasonId) return;

    // Determine WS URL based on environment or fallback.
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    let cancelled = false;
    const connect = async () => {
      let ticket: string;
      try {
        const response = await apiRequest<{ ticket: string; expiresInSeconds: number }>(
          "/ws/ticket",
          { method: "POST" }
        );
        ticket = response.ticket;
      } catch {
        if (!cancelled) setIsConnected(false);
        return;
      }
      if (cancelled) return;

      let wsUrl = `${protocol}//${host}/api/v1/ws/seasons/${seasonId}/stages/${stageId}/race?ticket=${encodeURIComponent(ticket)}`;

      // Add starting tires to URL
      if (startingTires) {
        Object.entries(startingTires).forEach(([driverId, compound]) => {
          wsUrl += `&tire_${driverId}=${compound}`;
        });
      }

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (cancelled) {
          ws.close();
          return;
        }
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        if (cancelled) return;
        try {
          const rawData = JSON.parse(event.data);
          const parsed = normalizeLivePayload(rawData);

          if (!parsed) {
            console.error("Invalid WS payload:", rawData);
            return;
          }

          const { type, cars, weather, totalLaps } = parsed;
          const finished = isFinishedPayload(type, cars);
          if (finished) {
            clearTransientNotifications();
          } else {
            setBroadcastQueue((previous) =>
              enqueueBroadcastEvents(
                previous,
                parsed.broadcastEvents,
                Date.now(),
                broadcastSeenIdsRef.current
              )
            );
          }

          if (cars.length > 0) {
            // Map cars to leaderboard
            const newLeaderboard: LeaderboardEntry[] = cars.map((car) => ({
              id: car.id,
              driverId: car.driverId,
              position: car.position,
              pilotName: car.pilotName,
              teamId: car.teamId,
              teamColor: car.teamColor,
              gap: car.gap,
              lap: car.lap,
              tireCompound: car.tires?.compound,
              tireCondition: car.tires?.condition,
              gridPosition: car.gridPosition,
              gridRow: car.gridRow,
              gridLane: car.gridLane,
              laneOffsetMeters: car.laneOffsetMeters,
              speed: car.speed,
              gapToAheadMs: car.gapToAheadMs,
              gapToLeaderMs: car.gapToLeaderMs,
              isAttacking: car.isAttacking,
              attackTargetId: car.attackTargetId,
              duelId: car.duelId,
              duelPhase: car.duelPhase,
              duelRole: car.duelRole,
              pitPhase: car.pitPhase,
              pitServiceDurationSeconds: car.pitServiceDurationSeconds,
              pitServiceElapsedSeconds: car.pitServiceElapsedSeconds,
              pitWaitingSeconds: car.pitWaitingSeconds,
              pitElapsedSeconds: car.pitElapsedSeconds,
              status: car.status,
              lastLapTimeMs: car.lastLapTimeMs,
              lastLapNumber: car.lastLapNumber,
              personalBestLapTimeMs: car.personalBestLapTimeMs,
              personalBestLapNumber: car.personalBestLapNumber,
              maxSpeedKph: car.maxSpeedKph,
              isFastestLap: car.isFastestLap
            }));
            setLeaderboard(newLeaderboard);
            setTimingCueStore((previous) =>
              mergeTimingCueStore(previous, parsed.timingCues, Date.now())
            );

            // Map cars to positions
            const newPositions: CarPosition[] = cars.map((car) => ({
              driver_id: car.driverId,
              pilot_name: car.pilotName,
              team_id: car.teamId,
              team_color: car.teamColor,
              lap_percentage: car.lapProgress,
              distance_meters: car.distanceMeters,
              position: car.position,
              grid_position: car.gridPosition,
              grid_row: car.gridRow,
              grid_lane: car.gridLane,
              lane_offset_meters: car.laneOffsetMeters,
              is_attacking: car.isAttacking,
              attack_target_id: car.attackTargetId,
              duel_id: car.duelId,
              duel_phase: car.duelPhase,
              duel_role: car.duelRole,
              status: car.status
            }));
            setCarPositions(newPositions);

            if (
              !finished &&
              parsed.notification?.message &&
              !isBackendTeamPitCall(parsed.notification)
            ) {
              const notifiedCar = cars.find(
                (car) =>
                  car.driverId === parsed.notification?.driverId ||
                  car.id === parsed.notification?.carId
              );
              showRadioMessage({
                id: `${parsed.notification?.carId || parsed.notification?.driverId}-${Date.now()}`,
                driverId: parsed.notification?.driverId || parsed.notification?.carId || "",
                pilotName: parsed.notification?.pilotName || "DRV",
                teamId: parsed.notification?.teamId || notifiedCar?.teamId || "",
                teamColor: parsed.notification?.teamColor || notifiedCar?.teamColor || "#64748b",
                source: parsed.notification?.source || "driver",
                text: parsed.notification?.message || "",
                timestamp: Date.now()
              });
            }

            // Map status
            const firstCarLap = cars[0]?.lap || 1;
            setRaceStatus((prev) => ({
              ...prev,
              currentLap: firstCarLap,
              totalLaps: totalLaps ?? prev.totalLaps,
              precipitation: weather?.precipitation ?? prev.precipitation,
              trackTemp: weather?.trackTemp ?? prev.trackTemp,
              rainIntensity: weather?.rainIntensity ?? prev.rainIntensity,
              trackWetness: weather?.trackWetness ?? prev.trackWetness,
              gameTimeRate: parsed.gameTimeRate ?? prev.gameTimeRate
            }));
          }

          if (finished) {
            setRaceStatus((prev) => ({ ...prev, isFinished: true }));
          }
        } catch (err) {
          console.error("Failed to parse WS message:", err);
        }
      };

      ws.onclose = () => {
        if (cancelled) return;
        setIsConnected(false);
      };
    };
    void connect();

    return () => {
      cancelled = true;
      if (
        wsRef.current?.readyState === WebSocket.OPEN ||
        wsRef.current?.readyState === WebSocket.CONNECTING
      ) {
        wsRef.current.close();
      }
      wsRef.current = null;
      clearTransientNotifications();
    };
  }, [stageId, seasonId, startingTires, enabled]);

  useEffect(() => {
    if (!radioMessage) return;
    const timer = window.setTimeout(
      () => {
        setRadioMessage((current) => expireRadioMessage(current, Date.now()));
      },
      Math.max(0, radioMessage.timestamp + RADIO_DURATION_MS - Date.now())
    );
    return () => window.clearTimeout(timer);
  }, [radioMessage]);

  useEffect(() => {
    if (!broadcastQueue.active) return;
    const remaining = Math.max(
      0,
      broadcastQueue.active.startedAtMs + BROADCAST_DURATION_MS - Date.now()
    );
    const timer = window.setTimeout(() => {
      setBroadcastQueue((previous) => advanceBroadcastQueue(previous, Date.now()));
    }, remaining);
    return () => window.clearTimeout(timer);
  }, [broadcastQueue.active]);

  const sendCommand = (action: string, carId: string, data: Record<string, unknown> = {}) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action, carId, ...data }));
    }
  };

  return {
    isConnected,
    raceStatus,
    leaderboard,
    carPositions,
    radioMessage,
    timingCues: timingCueStore.active,
    broadcastEvent: broadcastQueue.active?.event ?? null,
    showRadioMessage,
    sendCommand
  };
}
