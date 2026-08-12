from __future__ import annotations

import random
from dataclasses import dataclass, field, replace
from decimal import Decimal
from hashlib import sha256
from typing import Any

from app.domain.constants import F1_POINTS_BY_POSITION
from app.domain.enums import (
    CarCondition,
    EventSeverity,
    RaceEventType,
    ResultStatus,
    TrackSegmentType,
)
from app.models import Car
from app.services.pit_lane import (
    PIT_LANE_LENGTH_METERS as PIT_LANE_LENGTH,
)
from app.services.pit_lane import (
    PIT_LANE_SPEED_MPS as PIT_LANE_SPEED,
)
from app.services.pit_lane import (
    PIT_SERVICE_POINT_METERS as PIT_SERVICE_POINT,
)
from app.services.simulation import RaceSimulationResult
from app.services.tire_strategy import StrategyStint
from app.services.tires import (
    SLICK_COMPOUNDS,
    TIRE_COMPOUNDS,
    WET_WEATHER_COMPOUNDS,
    dry_tire_rule_required,
    dry_tire_rule_satisfied,
    tire_grip_multiplier,
    tire_wear_for_distance,
)
from app.services.track_geometry import TrackGeometryProfile
from app.services.weather import (
    precipitation_from_rain,
    race_weather_at,
    update_track_wetness,
)

# Constants for Physics
TIRE_WARNING_THRESHOLD = 40.0

# Stage 2 Setup Balance Constants
MAX_SETUP_BONUS = 0.05
MAX_SETUP_PENALTY = 0.03

BOT_WEATHER_TIRE_COOLDOWN_LAPS = 2
PHYSICS_SUBSTEP_SECONDS = 0.5
MIN_ACCEL_MPS2 = 3.0
MAX_ACCEL_MPS2 = 14.0
MAX_BRAKE_MPS2 = 38.0
GRID_ROW_SPACING_METERS = 12.0
GRID_SLOT_STAGGER_METERS = 6.0
GRID_FRONT_OFFSET_METERS = 6.0
GRID_LANE_OFFSET_METERS = 4.5
LAUNCH_PHASE_DISTANCE_METERS = 100.0
LAUNCH_MIN_FOLLOW_DISTANCE_METERS = 9.0
MIN_FOLLOW_DISTANCE_METERS = 18.0
ATTACK_WINDOW_METERS = 35.0
ATTACK_MIN_DISTANCE_METERS = 3.0
OVERTAKE_RANGE_METERS = 8.0
OVERTAKE_MARGIN_METERS = 2.0
DIRTY_AIR_RANGE_METERS = 95.0
DIRTY_AIR_MAX_PENALTY = 0.075
SLIPSTREAM_BONUS = 0.035
RACE_VARIANCE = 0.012
GRID_POSITION_HOLD_METERS = 45.0
FINISHED_COOLDOWN_SPEED_MPS = 28.0
DUEL_SIDE_OFFSET_METERS = GRID_LANE_OFFSET_METERS
MAX_VALID_LAP_SPEED_MPS = 150.0


@dataclass(frozen=True)
class TrackSegmentSnapshot:
    id: int
    segment_index: int
    type: TrackSegmentType
    length_meters: float | Decimal
    base_speed: float | Decimal
    overtake_chance: float | Decimal


@dataclass
class LiveRaceDuel:
    id: str
    attacker_id: str
    defender_id: str
    phase: str
    phase_started_tick: int
    outcome: str | None = None


@dataclass
class LiveRaceCarState:
    id: str
    pilot_name: str
    team_color: str
    current_segment_id: int
    # Simulation fixtures may omit a catalog team. The live endpoint always supplies it.
    team_id: str = ""
    driver_id: str = ""
    driver_code: str = ""
    driver_pace: int = 50
    driver_stability: int = 50

    # Base Stats
    engine_power: int = 50
    aero_efficiency: int = 50
    chassis_grip: int = 50
    reliability: int = 50
    condition: CarCondition = CarCondition.HEALTHY

    # Setup Settings
    wings_setting: int = 50
    suspension_setting: int = 50
    gearbox_setting: int = 50

    # Psychology (Stage 5)
    confidence: float = 50.0

    progress: float = 0.0
    lap: int = 0
    grid_position: int = 1
    event_type: RaceEventType = RaceEventType.CLEAN_RACE
    setup_multiplier: float = 1.0
    tire_multiplier: float = 1.0
    reliability_multiplier: float = 1.0
    driver_confidence_multiplier: float = 1.0
    tire_compound: str = "Medium"
    tire_condition: float = 100.0
    current_speed_mps: float = 0.0
    status: str = "RACING"  # RACING, PIT_REQUESTED, IN_PITS, DNF, FINISHED
    pit_timer: float = 0.0
    target_tire_compound: str | None = None
    dnf_reason: str | None = None
    resulting_condition: CarCondition | None = None
    finish_time: float | None = None
    classified_laps: int | None = None
    is_attacking: bool = False
    attack_target_id: str | None = None
    absolute_distance: float | None = None
    grid_row: int | None = None
    grid_lane: int | None = None
    lane_offset_meters: float = 0.0
    duel_id: str | None = None
    duel_phase: str = "NONE"
    duel_role: str | None = None
    lap_started_at: float = 0.0
    last_lap_time_ms: int | None = None
    last_lap_number: int | None = None
    personal_best_lap_time_ms: int | None = None
    personal_best_lap_number: int | None = None
    max_speed_kph: float = 0.0

    # Anti-spam flags for triggers
    cliff_triggered: bool = False
    last_rain_trigger_tick: int = -999
    last_weather_tire_change_lap: int = -999
    used_tire_compounds: list[str] = field(default_factory=list)
    tire_rule_warning_sent: bool = False
    strategy_plan: tuple[StrategyStint, ...] = ()
    strategy_stint_index: int = 0
    target_strategy_stint_index: int | None = None
    pit_entry_time: float | None = None
    pit_exit_time: float | None = None
    pit_available_from: float = 0.0
    pit_phase: str | None = None
    pit_service_start_time: float | None = None
    pit_service_release_time: float | None = None
    pit_service_duration_seconds: float | None = None
    pit_service_elapsed_seconds: float = 0.0
    pit_waiting_seconds: float = 0.0


class LiveRaceEngine:
    def __init__(
        self,
        *,
        segments: list[TrackSegmentSnapshot],
        cars: list[LiveRaceCarState],
        track_length_meters: float | Decimal,
        total_laps: int = 1,
        player_driver_ids: list[str] | None = None,
        tick_game_seconds: float = 1.0,
        initial_track_temp: float = 35.0,
        initial_track_wetness: float = 0.0,
        weather_keyframes: list[dict[str, Any]] | None = None,
        climate: dict[str, float] | None = None,
        weather_seed: int | None = None,
        track_geometry: TrackGeometryProfile | None = None,
        seed: int | None = None,
    ) -> None:
        if not segments:
            raise ValueError("Live race engine requires at least one track segment.")
        self.segments = sorted(segments, key=lambda segment: segment.segment_index)
        self.cars = cars
        self.track_length_meters = float(track_length_meters)
        self.total_laps = total_laps
        self.player_driver_ids = player_driver_ids or []
        self.tick_game_seconds = tick_game_seconds
        self.tick_id = 0
        self.race_time = 0.0
        self.track_temp = initial_track_temp
        self.track_wetness = float(initial_track_wetness)
        self.rain_intensity = 0.0
        self.weather_keyframes = weather_keyframes or []
        self.climate = climate or {}
        if self.weather_keyframes:
            start_weather = race_weather_at(self.weather_keyframes, 0.0)
            self.rain_intensity = float(start_weather["rainIntensity"])
            self.track_wetness = float(start_weather["trackWetness"])
        self.track_geometry = track_geometry
        self._segment_by_id = {segment.id: segment for segment in self.segments}
        self._segment_offsets = self._build_segment_offsets()

        self.rng = random.Random(seed)
        self._race_bias_by_car_id = {
            car.id: self._stable_signed_fraction(f"pace:{car.id}") * RACE_VARIANCE
            for car in self.cars
        }
        self._race_phase_by_car_id = {
            car.id: self._stable_signed_fraction(f"phase:{car.id}") * 3.14159 for car in self.cars
        }

        # Track previous rankings for overtakes
        self._last_positions: dict[str, int] = {}

        # Track finish order to preserve final standings
        self._finish_order: list[str] = []
        self._active_duels: dict[str, LiveRaceDuel] = {}
        self._next_duel_number = 1
        self._launch_phase_enabled = False
        self._tick_timing_cues: list[dict[str, Any]] = []
        self._tick_broadcast_events: list[dict[str, Any]] = []
        self._broadcast_sequence = 1
        self._fastest_lap_baseline_ready = False
        self._timing_cue_sequence = 1
        self._fastest_lap_car_id: str | None = None
        self._fastest_lap_driver_id: str | None = None
        self._fastest_lap_time_ms: int | None = None
        self._fastest_lap_number: int | None = None
        self._final_lap_started = False

        for car in self.cars:
            if not car.used_tire_compounds:
                car.used_tire_compounds.append(car.tire_compound)

        self._initialize_absolute_distances()
        self._apply_starting_grid_offsets()
        self._update_rankings()
        initial_leader = next((car for car in self._ranked_cars() if car.status != "DNF"), None)
        self._confirmed_leader_id = initial_leader.id if initial_leader else None
        self._pending_leader_id: str | None = None
        self._pending_leader_ticks = 0

    def is_complete(self) -> bool:
        """Return whether every car has reached a terminal race status."""
        return bool(self.cars) and all(car.status in ("FINISHED", "DNF") for car in self.cars)

    def process_command(self, car_id: str, action: str, **kwargs: Any) -> None:
        car = next((c for c in self.cars if c.id == car_id), None)
        if not car or car.status in ("DNF", "FINISHED"):
            return

        if action == "BOX_THIS_LAP":
            if self._remaining_laps(car) <= 1:
                return
            car.status = "PIT_REQUESTED"
            car.target_tire_compound = kwargs.get("target_tires", "Medium")
        elif action == "RADIO_RESPONSE":
            # For Stage 5, player might praise pilot
            if kwargs.get("type") == "PRAISE":
                car.confidence = min(100.0, car.confidence + 5.0)

    def tick(self) -> dict[str, Any]:
        self.tick_id += 1
        self._tick_timing_cues = []
        self._tick_broadcast_events = []
        tick_start_time = self.race_time

        triggers: list[dict[str, Any]] = []
        self._advance_weather()

        self._update_launch_lane_offsets()

        for car in self._ranked_cars():
            if car.status == "DNF":
                continue
            if car.status == "FINISHED":
                self._advance_finished_car(car)
                continue

            if car.status in ("RACING", "PIT_REQUESTED"):
                segment = self._effective_segment(car)
                self._update_multipliers(car, segment)

                # Check for DNF (Mechanical failure)
                if self._check_for_dnf(car):
                    car.event_type = RaceEventType.DNF
                    triggers.append(
                        {
                            "carId": car.id,
                            "driverId": car.driver_id,
                            "type": "TECHNICAL_ISSUE",
                            "trigger": car.dnf_reason,
                        }
                    )
                    continue

                self._advance_racing_car(car, tick_start_time)

                # Check for Crash/Lockup
                incident = self._check_for_incidents(car, self._effective_segment(car))
                if incident:
                    if car.status == "DNF":
                        car.event_type = RaceEventType.DNF
                    elif car.event_type != RaceEventType.DNF:
                        car.event_type = RaceEventType.DAMAGE
                    triggers.append(
                        {
                            "carId": car.id,
                            "driverId": car.driver_id,
                            "type": "INCIDENT",
                            "trigger": incident,
                        }
                    )

                # Tactical Triggers with Anti-Spam
                if self._current_wetness(car) > 0.1 and car.tire_compound in (
                    "Soft",
                    "Medium",
                    "Hard",
                ):
                    if self.tick_id - car.last_rain_trigger_tick > 60:
                        triggers.append(
                            {
                                "carId": car.id,
                                "driverId": car.driver_id,
                                "type": "RAIN_ON_SLICKS",
                                "trigger": "Слики не работают на мокрой трассе",
                            }
                        )
                        car.last_rain_trigger_tick = self.tick_id

                if car.tire_condition < TIRE_WARNING_THRESHOLD and not car.cliff_triggered:
                    triggers.append(
                        {
                            "carId": car.id,
                            "driverId": car.driver_id,
                            "type": "CLIFF_REACHED",
                            "trigger": "Шины скоро потеряют рабочее сцепление",
                        }
                    )
                    car.cliff_triggered = True

                # BOT AI Logic: only if NOT a player car AND status is RACING
                is_player_car = car.driver_id in self.player_driver_ids
                if (
                    is_player_car
                    and 2 <= self._remaining_laps(car) <= 3
                    and not self._dry_tire_rule_satisfied(car)
                    and not car.tire_rule_warning_sent
                ):
                    triggers.append(
                        {
                            "carId": car.id,
                            "driverId": car.driver_id,
                            "type": "TIRE_RULE_WARNING",
                            "trigger": "Нужно использовать вторую спецификацию сухих шин",
                        }
                    )
                if not is_player_car and car.status == "RACING":
                    if self._should_bot_pit(car):
                        car.status = "PIT_REQUESTED"
                        car.target_tire_compound = self._choose_bot_target_tire(car)

        self._advance_pit_lane_cars(tick_start_time)
        self._finish_cars_at_race_distance()

        self._resolve_traffic_and_duels()
        self._update_launch_lane_offsets()
        self._update_rankings()
        self.race_time = tick_start_time + self.tick_game_seconds
        self._record_confirmed_leader_change()
        snap = self.snapshot()
        return {
            **snap,
            "triggers": triggers,
            "timingCues": list(self._tick_timing_cues),
            "broadcastEvents": list(self._tick_broadcast_events),
        }

    def _record_confirmed_leader_change(self) -> None:
        leader = next((car for car in self._ranked_cars() if car.status != "DNF"), None)
        if leader is None or leader.id == self._confirmed_leader_id:
            self._pending_leader_id = None
            self._pending_leader_ticks = 0
            return

        if leader.id != self._pending_leader_id:
            self._pending_leader_id = leader.id
            self._pending_leader_ticks = 1
            return

        self._pending_leader_ticks += 1
        if self._pending_leader_ticks < 2:
            return

        self._confirmed_leader_id = leader.id
        self._pending_leader_id = None
        self._pending_leader_ticks = 0
        self._tick_broadcast_events.append(
            {
                "id": f"leader-changed-{self.tick_id}-{leader.id}-{self._broadcast_sequence}",
                "type": "LEADER_CHANGED",
                "carId": leader.id,
                "driverId": leader.driver_id,
                "pilotName": leader.pilot_name,
                "pilotCode": (leader.driver_code or leader.pilot_name[:3]).upper(),
                "teamId": leader.team_id,
                "teamColor": leader.team_color,
                "lapTimeMs": None,
                "lapNumber": None,
                "occurredAtRaceTime": self.race_time,
            }
        )
        self._broadcast_sequence += 1

    def snapshot(self) -> dict[str, Any]:
        ranked_cars = self._ranked_cars()

        cars_payload = []
        previous_car_dist = 0.0

        for position, car in enumerate(ranked_cars, start=1):
            car_dist = self._total_distance(car)
            leader_dist = self._total_distance(ranked_cars[0]) if ranked_cars else car_dist

            if position == 1:
                gap_str = "Лидер" if car.status != "DNF" else "Сход"
            elif car.status == "DNF":
                gap_str = "Сход"
            elif car.status == "FINISHED" and ranked_cars[0].status == "FINISHED":
                gap_str = self._format_final_gap(car, ranked_cars[0], position)
            else:
                dist_diff = previous_car_dist - car_dist
                gap_str = self._format_live_gap(dist_diff)

            gap_to_ahead_ms = None
            gap_to_leader_ms = None
            if position > 1 and car.status != "DNF":
                speed_for_gap = max(car.current_speed_mps, 45.0)
                gap_to_ahead_ms = max(
                    0,
                    round((previous_car_dist - car_dist) / speed_for_gap * 1000),
                )
                gap_to_leader_ms = max(0, round((leader_dist - car_dist) / speed_for_gap * 1000))

            cars_payload.append(
                {
                    "id": car.id,
                    "driverId": car.driver_id,
                    "pilotName": car.pilot_name,
                    "teamId": car.team_id,
                    "teamColor": car.team_color,
                    "position": position,
                    "gridPosition": car.grid_position,
                    "gridRow": car.grid_row,
                    "gridLane": car.grid_lane,
                    "laneOffsetMeters": round(car.lane_offset_meters, 3),
                    "lap": (
                        min(car.classified_laps or self.total_laps, self.total_laps)
                        if car.status == "FINISHED"
                        else car.lap + 1
                    ),
                    "segmentId": car.current_segment_id,
                    "progress": round(car.progress, 3),
                    "lapProgress": self.lap_progress(car),
                    "distanceMeters": round(car_dist, 3),
                    "speed": round(car.current_speed_mps, 3),
                    "lastLapTimeMs": car.last_lap_time_ms,
                    "lastLapNumber": car.last_lap_number,
                    "personalBestLapTimeMs": car.personal_best_lap_time_ms,
                    "personalBestLapNumber": car.personal_best_lap_number,
                    "maxSpeedKph": round(car.max_speed_kph, 3),
                    "isFastestLap": car.id == self._fastest_lap_car_id,
                    "gap": gap_str,
                    "gapToAheadMs": gap_to_ahead_ms,
                    "gapToLeaderMs": gap_to_leader_ms,
                    "isAttacking": car.is_attacking,
                    "attackTargetId": car.attack_target_id,
                    "duelId": car.duel_id,
                    "duelPhase": car.duel_phase,
                    "duelRole": car.duel_role,
                    "finishTime": round(car.finish_time, 3)
                    if car.finish_time is not None
                    else None,
                    "tires": {
                        "compound": car.tire_compound,
                        "condition": round(car.tire_condition, 3),
                    },
                    "usedTireCompounds": list(car.used_tire_compounds),
                    "dryTireRuleRequired": dry_tire_rule_required(car.used_tire_compounds),
                    "dryTireRuleSatisfied": self._dry_tire_rule_satisfied(car),
                    "psychology": {
                        "confidence": round(car.confidence, 1),
                    },
                    "status": car.status,
                    "pitPhase": car.pit_phase,
                    "pitServiceDurationSeconds": round(car.pit_service_duration_seconds, 3)
                    if car.pit_service_duration_seconds is not None
                    else None,
                    "pitServiceElapsedSeconds": round(car.pit_service_elapsed_seconds, 3),
                    "pitWaitingSeconds": round(car.pit_waiting_seconds, 3),
                    "pitElapsedSeconds": round(
                        max(0.0, self.race_time - car.pit_entry_time)
                        if car.status == "IN_PITS" and car.pit_entry_time is not None
                        else (
                            max(0.0, car.pit_exit_time - car.pit_entry_time)
                            if car.pit_exit_time is not None and car.pit_entry_time is not None
                            else 0.0
                        ),
                        3,
                    ),
                    "dnfReason": car.dnf_reason,
                }
            )
            previous_car_dist = car_dist

        return {
            "type": "TICK_UPDATE",
            "tickId": self.tick_id,
            "raceTime": self.race_time,
            "totalLaps": self.total_laps,
            "weather": {
                "precipitation": precipitation_from_rain(self.rain_intensity),
                "trackTemp": round(self.track_temp, 1),
                "rainIntensity": round(self.rain_intensity, 4),
                "trackWetness": round(self.track_wetness, 4),
            },
            "notification": None,
            "raceTiming": {
                "fastestLapCarId": self._fastest_lap_car_id,
                "fastestLapDriverId": self._fastest_lap_driver_id,
                "fastestLapTimeMs": self._fastest_lap_time_ms,
                "fastestLapNumber": self._fastest_lap_number,
            },
            "cars": cars_payload,
        }

    def _initialize_absolute_distances(self) -> None:
        for car in self.cars:
            if car.absolute_distance is None:
                car.absolute_distance = self._distance_from_lap_progress(car)
            if car.grid_row is None:
                car.grid_row = max(1, (car.grid_position + 1) // 2)
            if car.grid_lane is None:
                car.grid_lane = (car.grid_position - 1) % 2

    def _distance_from_lap_progress(self, car: LiveRaceCarState) -> float:
        return (
            car.lap * self.track_length_meters
            + self._segment_offsets[car.current_segment_id]
            + car.progress
        )

    def _grid_lane_offset(self, lane: int) -> float:
        return -GRID_LANE_OFFSET_METERS if lane == 0 else GRID_LANE_OFFSET_METERS

    def _grid_max_depth_meters(self) -> float:
        rows = max(1, (len(self.cars) + 1) // 2)
        return (
            GRID_FRONT_OFFSET_METERS
            + (rows - 1) * GRID_ROW_SPACING_METERS
            + GRID_SLOT_STAGGER_METERS
            + GRID_ROW_SPACING_METERS
        )

    def _apply_starting_grid_offsets(self) -> None:
        if len(self.cars) < 2:
            return
        if any(abs(self._total_distance(car)) > 0.001 for car in self.cars):
            return

        self._launch_phase_enabled = True
        ordered = sorted(self.cars, key=lambda car: (car.grid_position, car.id))
        for index, car in enumerate(ordered):
            row = index // 2 + 1
            lane = index % 2
            stagger = lane * GRID_SLOT_STAGGER_METERS
            distance = -(GRID_FRONT_OFFSET_METERS + (row - 1) * GRID_ROW_SPACING_METERS + stagger)
            car.grid_row = row
            car.grid_lane = lane
            car.lane_offset_meters = self._grid_lane_offset(lane)
            self._set_total_distance(car, distance)

    def _is_in_launch_phase(self, car: LiveRaceCarState) -> bool:
        return (
            self._launch_phase_enabled
            and self._total_distance(car) < LAUNCH_PHASE_DISTANCE_METERS
        )

    def _update_launch_lane_offsets(self) -> None:
        for car in self.cars:
            if self._is_in_launch_phase(car):
                distance_after_start = max(0.0, self._total_distance(car))
                lane_factor = 1.0 - distance_after_start / LAUNCH_PHASE_DISTANCE_METERS
                car.lane_offset_meters = self._grid_lane_offset(car.grid_lane or 0) * lane_factor
            elif car.duel_phase == "NONE":
                car.lane_offset_meters = 0.0

    def _format_live_gap(self, distance_gap: float) -> str:
        time_gap = max(0.0, distance_gap) / 50.0
        if time_gap > 60.0:
            return f"+{int(time_gap // 60)}:{time_gap % 60:06.3f}"
        return f"+{time_gap:.3f}с"

    def lap_progress(self, car: LiveRaceCarState) -> float:
        return round(self._lap_progress_unrounded(car), 6)

    def _lap_progress_unrounded(self, car: LiveRaceCarState) -> float:
        total_distance = self._total_distance(car)
        if total_distance < 0.0:
            wrapped = self.track_length_meters + total_distance
            return max(0.0, min(1.0, wrapped / self.track_length_meters))

        _, distance_on_lap = self._lap_and_distance_on_lap(total_distance)
        return max(0.0, min(1.0, distance_on_lap / self.track_length_meters))

    def _lap_and_distance_on_lap(self, total_distance: float) -> tuple[int, float]:
        """Split a non-negative canonical distance without losing fractional-track laps."""
        ratio = total_distance / self.track_length_meters
        nearest_lap = round(ratio)
        boundary = nearest_lap * self.track_length_meters
        if abs(total_distance - boundary) <= 1e-7:
            return max(0, nearest_lap), 0.0
        lap = max(0, int(ratio))
        return lap, total_distance - lap * self.track_length_meters

    def _next_lap_line_after(self, total_distance: float) -> float:
        lap, _ = self._lap_and_distance_on_lap(max(0.0, total_distance))
        return (lap + 1) * self.track_length_meters

    def _remaining_laps(self, car: LiveRaceCarState) -> int:
        return max(0, self.total_laps - car.lap)

    def _advance_weather(self) -> None:
        if self.weather_keyframes:
            active_cars = [car for car in self.cars if car.status != "DNF"]
            leader_distance = max((self._total_distance(car) for car in active_cars), default=0.0)
            race_progress = max(
                0.0,
                min(1.0, leader_distance / (self.track_length_meters * self.total_laps)),
            )
            scenario_weather = race_weather_at(self.weather_keyframes, race_progress)
            self.track_temp = float(scenario_weather["trackTemp"])
            self.rain_intensity = float(scenario_weather["rainIntensity"])
        self.track_wetness = update_track_wetness(
            self.track_wetness,
            self.rain_intensity,
            seconds=self.tick_game_seconds,
            track_temp_c=self.track_temp,
        )

    def _current_wetness(self, car: LiveRaceCarState) -> float:
        return self.track_wetness

    def _ai_wetness(self, car: LiveRaceCarState) -> float:
        return self.track_wetness

    def _weather_tire_target(self, car: LiveRaceCarState) -> str:
        """Choose a stable weather compound from both local and lap-wide conditions.

        The separated thresholds deliberately overlap. A car already on wets therefore
        does not immediately switch back when it reaches the dry half of a mixed track,
        while an intermediate runner waits for broadly wet conditions before moving to
        full wets.
        """
        average = self.track_wetness

        if car.tire_compound == "Wet":
            if average <= 0.32:
                if average >= 0.06:
                    return "Intermediate"
                return self._choose_dry_tire(car)
            return "Wet"

        if car.tire_compound == "Intermediate":
            if average >= 0.52:
                return "Wet"
            if average <= 0.05:
                return self._choose_dry_tire(car)
            return "Intermediate"

        if average >= 0.58:
            return "Wet"
        if average >= 0.11:
            return "Intermediate"
        return car.tire_compound

    def _choose_dry_tire(self, car: LiveRaceCarState) -> str:
        planned_index = self._strategy_index_for_lap(car, max(1, car.lap + 1))
        if planned_index is not None:
            planned_compound = car.strategy_plan[planned_index].compound
            if planned_compound in SLICK_COMPOUNDS:
                return planned_compound
        remaining_laps = self._remaining_laps(car)
        if remaining_laps <= 4:
            return "Soft"
        if remaining_laps >= 14 or self.track_temp >= 42.0:
            return "Hard"
        return "Medium"

    def _choose_bot_target_tire(self, car: LiveRaceCarState) -> str:
        weather_target = self._weather_tire_target(car)
        if weather_target in WET_WEATHER_COMPOUNDS or car.tire_compound in WET_WEATHER_COMPOUNDS:
            if weather_target in WET_WEATHER_COMPOUNDS:
                plan_target = self._planned_target_index(car)
                car.target_strategy_stint_index = (
                    plan_target
                    if plan_target is not None
                    and car.strategy_plan[plan_target].compound == weather_target
                    else None
                )
            else:
                car.target_strategy_stint_index = self._strategy_index_for_lap(
                    car,
                    max(1, car.lap + 1),
                )
            return weather_target
        plan_target = self._planned_target_index(car)
        if plan_target is not None:
            car.target_strategy_stint_index = plan_target
            return car.strategy_plan[plan_target].compound
        if self._remaining_laps(car) <= 4 and not self._dry_tire_rule_satisfied(car):
            car.target_strategy_stint_index = None
            return self._rule_compliance_target(car)
        car.target_strategy_stint_index = None
        return self._choose_dry_tire(car)

    def _should_bot_pit(self, car: LiveRaceCarState) -> bool:
        if car.status != "RACING":
            return False

        remaining_laps = self._remaining_laps(car)
        if remaining_laps <= 1:
            return False

        weather_target = self._weather_tire_target(car)
        weather_change = weather_target != car.tire_compound and bool(
            {weather_target, car.tire_compound} & WET_WEATHER_COMPOUNDS
        )
        if weather_change:
            switching_between_rain_tires = (
                weather_target in WET_WEATHER_COMPOUNDS
                and car.tire_compound in WET_WEATHER_COMPOUNDS
            )
            if switching_between_rain_tires:
                laps_since_weather_change = car.lap - car.last_weather_tire_change_lap
                return laps_since_weather_change >= BOT_WEATHER_TIRE_COOLDOWN_LAPS
            return True

        if remaining_laps <= 4 and not self._dry_tire_rule_satisfied(car):
            return True

        plan_target = self._planned_target_index(car)
        if plan_target is not None:
            return car.strategy_plan[plan_target].compound != car.tire_compound or (
                plan_target > car.strategy_stint_index
            )

        return car.tire_condition < 30.0

    def _strategy_index_for_lap(
        self,
        car: LiveRaceCarState,
        lap: int,
    ) -> int | None:
        for index, stint in enumerate(car.strategy_plan):
            if stint.start_lap <= lap <= stint.end_lap:
                return index
        return len(car.strategy_plan) - 1 if car.strategy_plan else None

    def _planned_target_index(self, car: LiveRaceCarState) -> int | None:
        if not car.strategy_plan:
            return None
        weather_target = self._weather_tire_target(car)
        current_index = min(car.strategy_stint_index, len(car.strategy_plan) - 1)
        current_stint = car.strategy_plan[current_index]
        if car.lap >= current_stint.end_lap and current_index + 1 < len(car.strategy_plan):
            next_compound = car.strategy_plan[current_index + 1].compound
            if (
                next_compound in WET_WEATHER_COMPOUNDS
                and next_compound != weather_target
            ):
                return None
            return current_index + 1

        expected_index = self._strategy_index_for_lap(car, max(1, car.lap + 1))
        if (
            expected_index is not None
            and car.strategy_plan[expected_index].compound != car.tire_compound
        ):
            if (
                car.strategy_plan[expected_index].compound in WET_WEATHER_COMPOUNDS
                and car.strategy_plan[expected_index].compound != weather_target
            ):
                return None
            return expected_index
        if car.tire_condition < 30.0 and current_index + 1 < len(car.strategy_plan):
            if (
                car.strategy_plan[current_index + 1].compound in WET_WEATHER_COMPOUNDS
                and car.strategy_plan[current_index + 1].compound != weather_target
            ):
                return None
            return current_index + 1
        return None

    def _dry_tire_rule_satisfied(self, car: LiveRaceCarState) -> bool:
        return dry_tire_rule_satisfied(car.used_tire_compounds)

    def _rule_compliance_target(self, car: LiveRaceCarState) -> str:
        used_slicks = set(car.used_tire_compounds) & SLICK_COMPOUNDS
        preferred = self._choose_dry_tire(car)
        if preferred not in used_slicks:
            return preferred
        return next(
            compound for compound in ("Soft", "Medium", "Hard") if compound not in used_slicks
        )

    def _update_rankings(self) -> None:
        ranked = self._ranked_cars()
        for pos, car in enumerate(ranked, start=1):
            prev_pos = self._last_positions.get(car.id)
            if prev_pos and pos < prev_pos and car.status == "RACING":
                # Successful overtake!
                car.confidence = min(100.0, car.confidence + 2.0)
            self._last_positions[car.id] = pos

    def _update_multipliers(self, car: LiveRaceCarState, segment: TrackSegmentSnapshot) -> None:
        car.tire_multiplier = self._calculate_tire_multiplier(car)
        car.setup_multiplier = self._calculate_setup_multiplier(car, segment)
        car.reliability_multiplier = self._calculate_reliability_multiplier(car)
        car.driver_confidence_multiplier = self._calculate_confidence_multiplier(car)

    def _calculate_tire_multiplier(self, car: LiveRaceCarState) -> float:
        return tire_grip_multiplier(
            car.tire_compound,
            car.tire_condition,
            track_temperature_c=self.track_temp,
            wetness=self._current_wetness(car),
        )

    def _calculate_reliability_multiplier(self, car: LiveRaceCarState) -> float:
        # Reliability affects technical-failure risk, not hidden pace degradation.
        return 1.0

    def _calculate_confidence_multiplier(self, car: LiveRaceCarState) -> float:
        # Stage 5 psychology
        conf = car.confidence
        if conf >= 50:
            # Bonus up to +1.5%
            bonus = ((conf - 50) / 50) * 0.015
            return 1.0 + bonus
        else:
            # Penalty up to -2.0%
            penalty = ((50 - conf) / 50) * 0.020
            return 1.0 - penalty

    def _calculate_setup_multiplier(
        self,
        car: LiveRaceCarState,
        segment: TrackSegmentSnapshot,
    ) -> float:
        if segment.type == TrackSegmentType.STRAIGHT:
            base_score = (car.engine_power * 0.7 + car.aero_efficiency * 0.3) / 100.0
            ideal_wings, ideal_suspension, ideal_gearbox = 0, None, 100
        elif segment.type == TrackSegmentType.HIGH_SPEED_CORNER:
            base_score = (car.aero_efficiency * 0.8 + car.chassis_grip * 0.2) / 100.0
            ideal_wings, ideal_suspension, ideal_gearbox = 100, 100, None
        elif segment.type == TrackSegmentType.LOW_SPEED_CORNER:
            base_score = (car.chassis_grip * 0.8 + car.engine_power * 0.2) / 100.0
            ideal_wings, ideal_suspension, ideal_gearbox = None, 0, 0
        else:
            base_score = (car.engine_power + car.aero_efficiency + car.chassis_grip) / 300.0
            ideal_wings, ideal_suspension, ideal_gearbox = 50, 50, 50

        penalties = []
        if ideal_wings is not None:
            penalties.append(abs(car.wings_setting - ideal_wings) / 100.0)
        if ideal_suspension is not None:
            penalties.append(abs(car.suspension_setting - ideal_suspension) / 100.0)
        if ideal_gearbox is not None:
            penalties.append(abs(car.gearbox_setting - ideal_gearbox) / 100.0)

        total_penalty = sum(penalties) / len(penalties) if penalties else 0.0
        return 1.0 + (base_score * MAX_SETUP_BONUS) - (total_penalty * MAX_SETUP_PENALTY)

    def _actual_speed(
        self,
        car: LiveRaceCarState,
        segment: TrackSegmentSnapshot,
    ) -> float:
        base_speed = self._target_base_speed(car, segment)
        return (
            base_speed
            * car.setup_multiplier
            * car.tire_multiplier
            * car.reliability_multiplier
            * car.driver_confidence_multiplier
            * self._condition_multiplier(car)
            * self._race_variance_multiplier(car)
            * self._traffic_speed_multiplier(car, segment)
        )

    def _target_base_speed(self, car: LiveRaceCarState, segment: TrackSegmentSnapshot) -> float:
        if self.track_geometry is None:
            return float(segment.base_speed)
        return self.track_geometry.target_speed(self._lap_progress_unrounded(car))

    def _effective_segment(self, car: LiveRaceCarState) -> TrackSegmentSnapshot:
        segment = self._segment_by_id[car.current_segment_id]
        if self.track_geometry is None:
            return segment
        segment_type = self.track_geometry.segment_type(self._lap_progress_unrounded(car))
        return replace(segment, type=segment_type, base_speed=self._target_base_speed(car, segment))

    def _advance_racing_car(self, car: LiveRaceCarState, tick_start_time: float) -> float:
        remaining = self.tick_game_seconds
        elapsed = 0.0
        total_distance = 0.0
        while remaining > 0 and car.status in ("RACING", "PIT_REQUESTED"):
            step = min(PHYSICS_SUBSTEP_SECONDS, remaining)
            segment = self._effective_segment(car)
            self._update_multipliers(car, segment)
            target_speed = self._actual_speed(car, segment)
            car.current_speed_mps = self._approach_speed(
                car.current_speed_mps,
                target_speed,
                step,
            )
            car.max_speed_kph = max(car.max_speed_kph, car.current_speed_mps * 3.6)
            distance = car.current_speed_mps * step
            distance_before = self._total_distance(car)
            classification_target = self._classification_target_distance(distance_before)
            next_lap_line = self._next_lap_line_after(distance_before)
            crossed_classification_line = (
                classification_target is not None
                and distance_before < classification_target <= distance_before + distance
            )
            is_pit_entry_crossing = (
                car.status == "PIT_REQUESTED"
                and next_lap_line < self.track_length_meters * self.total_laps
                and (
                    classification_target is None
                    or next_lap_line < classification_target
                )
                and distance_before < next_lap_line <= distance_before + distance
            )
            if is_pit_entry_crossing:
                distance_to_entry = max(0.0, next_lap_line - distance_before)
                entry_seconds = step * distance_to_entry / distance if distance > 0.0 else 0.0
                total_distance += distance_to_entry
                self._apply_tire_wear(car, distance_to_entry, segment)
                self._set_total_distance(car, next_lap_line)
                entry_time = tick_start_time + elapsed + entry_seconds
                completed_lap = round(next_lap_line / self.track_length_meters)
                self._record_lap_crossing(car, completed_lap, entry_time)
                car.status = "IN_PITS"
                car.pit_timer = 0.0
                car.pit_service_duration_seconds = None
                car.pit_service_elapsed_seconds = 0.0
                car.pit_waiting_seconds = 0.0
                car.pit_service_start_time = None
                car.pit_service_release_time = None
                car.pit_service_duration_seconds = self._assign_pit_service_duration()
                car.pit_phase = "ENTRY"
                car.pit_entry_time = entry_time
                car.pit_exit_time = None
                car.pit_available_from = entry_time
                car.current_speed_mps = PIT_LANE_SPEED
                return total_distance

            total_distance += distance
            self._apply_tire_wear(car, distance, segment)
            self._capture_finish_time(
                car,
                distance_before,
                distance,
                tick_start_time + elapsed,
                step,
                classification_target,
            )
            crossed_lap_line = distance_before < next_lap_line <= distance_before + distance
            if crossed_lap_line:
                crossing_seconds = step * (next_lap_line - distance_before) / distance
                self._record_lap_crossing(
                    car,
                    round(next_lap_line / self.track_length_meters),
                    tick_start_time + elapsed + crossing_seconds,
                )
            self._set_total_distance(
                car,
                distance_before + distance,
                allow_beyond_finish=crossed_classification_line,
            )
            if crossed_classification_line and car.finish_time is not None:
                self._mark_finished(
                    car,
                    finish_time=car.finish_time,
                    classified_laps=int(round(classification_target / self.track_length_meters)),
                )
                return total_distance
            remaining -= step
            elapsed += step
        return total_distance

    def _advance_finished_car(self, car: LiveRaceCarState) -> None:
        distance_before = self._total_distance(car)
        if distance_before < 0.0:
            return

        car.current_speed_mps = FINISHED_COOLDOWN_SPEED_MPS
        self._set_total_distance(
            car,
            distance_before + FINISHED_COOLDOWN_SPEED_MPS * self.tick_game_seconds,
            allow_beyond_finish=True,
        )

    def _approach_speed(self, current: float, target: float, seconds: float) -> float:
        if seconds <= 0:
            return current

        if current < target:
            speed_ratio = current / max(target, 1.0)
            acceleration = MIN_ACCEL_MPS2 + (MAX_ACCEL_MPS2 - MIN_ACCEL_MPS2) * (1.0 - speed_ratio)
            return min(target, current + acceleration * seconds)

        if current > target:
            return max(target, current - MAX_BRAKE_MPS2 * seconds)

        return current

    def _capture_finish_time(
        self,
        car: LiveRaceCarState,
        distance_before: float,
        distance_added: float,
        step_start_time: float,
        step_seconds: float,
        classification_target: float | None = None,
    ) -> None:
        if car.finish_time is not None or distance_added <= 0:
            return

        finish_distance = classification_target or self.total_laps * self.track_length_meters
        distance_after = distance_before + distance_added
        if distance_before < finish_distance <= distance_after:
            ratio = (finish_distance - distance_before) / distance_added
            car.finish_time = step_start_time + step_seconds * max(0.0, min(1.0, ratio))

    def _record_lap_crossing(
        self, car: LiveRaceCarState, lap_number: int, crossing_time: float
    ) -> None:
        lap_time_ms = max(0, round((crossing_time - car.lap_started_at) * 1000))
        if lap_time_ms < self._minimum_valid_lap_time_ms():
            car.lap_started_at = crossing_time
            self._record_final_lap_start(car, lap_number, crossing_time)
            return

        car.last_lap_time_ms = lap_time_ms
        car.last_lap_number = lap_number
        if car.personal_best_lap_time_ms is None or lap_time_ms < car.personal_best_lap_time_ms:
            car.personal_best_lap_time_ms = lap_time_ms
            car.personal_best_lap_number = lap_number
        is_absolute_improvement = (
            self._fastest_lap_time_ms is None or lap_time_ms < self._fastest_lap_time_ms
        )
        if is_absolute_improvement:
            self._fastest_lap_car_id = car.id
            self._fastest_lap_driver_id = car.driver_id
            self._fastest_lap_time_ms = lap_time_ms
            self._fastest_lap_number = lap_number
        eligible = [item for item in self.cars if item.status != "DNF"]
        if not self._fastest_lap_baseline_ready:
            self._fastest_lap_baseline_ready = bool(eligible) and all(
                item.last_lap_time_ms is not None for item in eligible
            )
        elif is_absolute_improvement:
            self._tick_broadcast_events.append(
                {
                    "id": (
                        f"fastest-lap-{self.tick_id}-{car.id}-{lap_number}-"
                        f"{self._broadcast_sequence}"
                    ),
                    "type": "FASTEST_LAP",
                    "carId": car.id,
                    "driverId": car.driver_id,
                    "pilotName": car.pilot_name,
                    "pilotCode": (car.driver_code or car.pilot_name[:3]).upper(),
                    "teamId": car.team_id,
                    "teamColor": car.team_color,
                    "lapTimeMs": lap_time_ms,
                    "lapNumber": lap_number,
                    "occurredAtRaceTime": crossing_time,
                }
            )
            self._broadcast_sequence += 1
        self._record_final_lap_start(car, lap_number, crossing_time)
        car.lap_started_at = crossing_time
        cue_id = f"last-lap-{self.tick_id}-{self._timing_cue_sequence}"
        self._timing_cue_sequence += 1
        self._tick_timing_cues.append(
            {
                "id": cue_id,
                "type": "LAST_LAP",
                "carId": car.id,
                "driverId": car.driver_id,
                "lapNumber": lap_number,
                "lapTimeMs": lap_time_ms,
                "durationMs": 4000,
            }
        )

    def _record_final_lap_start(
        self, car: LiveRaceCarState, completed_lap: int, crossing_time: float
    ) -> None:
        if self.total_laps <= 1 or self._final_lap_started or completed_lap != self.total_laps - 1:
            return

        self._final_lap_started = True
        self._tick_broadcast_events.append(
            {
                "id": f"final-lap-started-{self.tick_id}-{car.id}-{self._broadcast_sequence}",
                "type": "FINAL_LAP_STARTED",
                "carId": car.id,
                "driverId": car.driver_id,
                "pilotName": car.pilot_name,
                "pilotCode": (car.driver_code or car.pilot_name[:3]).upper(),
                "teamId": car.team_id,
                "teamColor": car.team_color,
                "lapTimeMs": None,
                "lapNumber": self.total_laps,
                "occurredAtRaceTime": crossing_time,
            }
        )
        self._broadcast_sequence += 1

    def _minimum_valid_lap_time_ms(self) -> int:
        return round(self.track_length_meters / MAX_VALID_LAP_SPEED_MPS * 1000)

    def _classification_target_distance(self, distance_before: float) -> float | None:
        if distance_before < 0.0:
            return None

        race_distance = self.total_laps * self.track_length_meters
        if not self._finish_order:
            return race_distance

        next_line = self._next_lap_line_after(distance_before)
        if next_line <= race_distance:
            return next_line
        return None

    def _resolve_traffic_and_duels(self) -> None:
        contenders = [
            car for car in self._ranked_cars() if car.status in ("RACING", "PIT_REQUESTED")
        ]
        self._advance_live_duels()
        self._resolve_launch_traffic(contenders)
        active_duel_car_ids = self._active_duel_car_ids()
        for index in range(1, len(contenders)):
            ahead = contenders[index - 1]
            follower = contenders[index]
            ahead_distance = self._total_distance(ahead)
            follower_distance = self._total_distance(follower)
            distance_gap = ahead_distance - follower_distance

            if distance_gap <= 0:
                continue

            if self._is_in_launch_phase(ahead) or self._is_in_launch_phase(follower):
                continue

            if ahead.id in active_duel_car_ids or follower.id in active_duel_car_ids:
                if self._cars_share_active_duel(ahead, follower):
                    continue
                safe_gap = max(MIN_FOLLOW_DISTANCE_METERS, ATTACK_WINDOW_METERS * 0.7)
                if distance_gap < safe_gap:
                    self._set_total_distance(follower, ahead_distance - safe_gap)
                    follower.current_speed_mps = min(
                        follower.current_speed_mps,
                        max(ahead.current_speed_mps - 1.5, 0.0),
                    )
                continue

            if ahead.status != "RACING" or follower.status != "RACING":
                if distance_gap < MIN_FOLLOW_DISTANCE_METERS:
                    self._set_total_distance(follower, ahead_distance - MIN_FOLLOW_DISTANCE_METERS)
                continue

            attacking = self._should_attack(follower, ahead, distance_gap)
            if attacking:
                self._start_duel(follower, ahead)
                active_duel_car_ids.update({ahead.id, follower.id})
                continue

            if distance_gap < MIN_FOLLOW_DISTANCE_METERS:
                self._set_total_distance(follower, ahead_distance - MIN_FOLLOW_DISTANCE_METERS)
                follower.current_speed_mps = min(
                    follower.current_speed_mps,
                    max(ahead.current_speed_mps - 1.0, 0.0),
                )

    def _resolve_launch_traffic(self, contenders: list[LiveRaceCarState]) -> None:
        """Keep each grid lane safe without treating the two launch lanes as one train."""
        for lane in (0, 1):
            lane_cars = sorted(
                (car for car in contenders if car.grid_lane == lane),
                key=self._total_distance,
                reverse=True,
            )
            for index in range(1, len(lane_cars)):
                ahead = lane_cars[index - 1]
                follower = lane_cars[index]
                if not self._is_in_launch_phase(follower):
                    continue
                ahead_distance = self._total_distance(ahead)
                follower_distance = self._total_distance(follower)
                if ahead_distance - follower_distance < LAUNCH_MIN_FOLLOW_DISTANCE_METERS:
                    self._set_total_distance(
                        follower,
                        ahead_distance - LAUNCH_MIN_FOLLOW_DISTANCE_METERS,
                    )
                    follower.current_speed_mps = min(
                        follower.current_speed_mps,
                        max(ahead.current_speed_mps - 1.0, 0.0),
                    )

    def _active_duel_car_ids(self) -> set[str]:
        return {
            car_id
            for duel in self._active_duels.values()
            for car_id in (duel.attacker_id, duel.defender_id)
        }

    def _cars_share_active_duel(self, first: LiveRaceCarState, second: LiveRaceCarState) -> bool:
        same_duel = first.duel_id == second.duel_id
        return bool(first.duel_id and same_duel and second.duel_phase != "NONE")

    def _start_duel(self, attacker: LiveRaceCarState, defender: LiveRaceCarState) -> None:
        duel_id = f"duel-{self._next_duel_number}"
        self._next_duel_number += 1
        duel = LiveRaceDuel(
            id=duel_id,
            attacker_id=attacker.id,
            defender_id=defender.id,
            phase="APPROACH",
            phase_started_tick=self.tick_id,
        )
        self._active_duels[duel_id] = duel
        self._apply_duel_snapshot_state(duel)

    def _advance_live_duels(self) -> None:
        for _duel_id, duel in list(self._active_duels.items()):
            attacker = self._car_by_id(duel.attacker_id)
            defender = self._car_by_id(duel.defender_id)
            if attacker is None or defender is None:
                self._clear_duel(duel)
                continue
            if attacker.status not in ("RACING",) or defender.status not in ("RACING",):
                if duel.phase != "RETURN":
                    duel.phase = "RETURN"
                    duel.phase_started_tick = self.tick_id
                    duel.outcome = "ABORT"
                    self._apply_duel_snapshot_state(duel)
                elif self.tick_id > duel.phase_started_tick:
                    self._clear_duel(duel)
                continue
            if self.tick_id <= duel.phase_started_tick:
                self._apply_duel_snapshot_state(duel)
                continue

            ahead_distance = self._total_distance(defender)
            attacker_distance = self._total_distance(attacker)
            gap = abs(ahead_distance - attacker_distance)
            if gap > ATTACK_WINDOW_METERS * 2.0 and duel.phase not in ("RETURN",):
                duel.phase = "ABORT"
                duel.outcome = "ABORT"
                duel.phase_started_tick = self.tick_id
            elif duel.phase == "APPROACH":
                duel.phase = "MOVE_ASIDE"
                duel.phase_started_tick = self.tick_id
            elif duel.phase == "MOVE_ASIDE":
                duel.phase = "SIDE_BY_SIDE"
                duel.phase_started_tick = self.tick_id
            elif duel.phase == "SIDE_BY_SIDE":
                completed = self._should_complete_overtake(attacker, defender, gap)
                duel.outcome = "PASS" if completed else "ABORT"
                duel.phase = duel.outcome
                duel.phase_started_tick = self.tick_id
                if duel.outcome == "PASS":
                    defender_distance = self._total_distance(defender)
                    self._set_total_distance(
                        attacker,
                        min(
                            defender_distance + OVERTAKE_MARGIN_METERS,
                            self.total_laps * self.track_length_meters - 0.01,
                        ),
                    )
                    attacker.confidence = min(100.0, attacker.confidence + 1.5)
                else:
                    self._keep_aborted_duel_safe(attacker, defender)
            elif duel.phase in ("PASS", "ABORT"):
                duel.phase = "RETURN"
                duel.phase_started_tick = self.tick_id
            elif duel.phase == "RETURN":
                self._clear_duel(duel)
                continue

            self._apply_duel_snapshot_state(duel)

    def _keep_aborted_duel_safe(
        self, attacker: LiveRaceCarState, defender: LiveRaceCarState
    ) -> None:
        defender_distance = self._total_distance(defender)
        attacker_distance = self._total_distance(attacker)
        if attacker_distance >= defender_distance - ATTACK_MIN_DISTANCE_METERS:
            self._set_total_distance(attacker, defender_distance - ATTACK_MIN_DISTANCE_METERS)

    def _apply_duel_snapshot_state(self, duel: LiveRaceDuel) -> None:
        attacker = self._car_by_id(duel.attacker_id)
        defender = self._car_by_id(duel.defender_id)
        if attacker is None or defender is None:
            return
        for car, role, target in (
            (attacker, "ATTACKER", defender.id),
            (defender, "DEFENDER", attacker.id),
        ):
            car.duel_id = duel.id
            car.duel_phase = duel.phase
            car.duel_role = role
            car.attack_target_id = target
            car.is_attacking = role == "ATTACKER" and duel.phase not in ("RETURN", "NONE")
            if duel.phase in ("MOVE_ASIDE", "SIDE_BY_SIDE", "PASS", "ABORT"):
                car.lane_offset_meters = (
                    DUEL_SIDE_OFFSET_METERS if role == "ATTACKER" else -DUEL_SIDE_OFFSET_METERS
                )
            elif duel.phase == "RETURN":
                car.lane_offset_meters = 0.0
            else:
                car.lane_offset_meters = 0.0

    def _clear_duel(self, duel: LiveRaceDuel) -> None:
        for car_id in (duel.attacker_id, duel.defender_id):
            car = self._car_by_id(car_id)
            if car is None:
                continue
            car.duel_id = None
            car.duel_phase = "NONE"
            car.duel_role = None
            car.attack_target_id = None
            car.is_attacking = False
            if self._total_distance(car) >= 0.0:
                car.lane_offset_meters = 0.0
        self._active_duels.pop(duel.id, None)

    def _car_by_id(self, car_id: str) -> LiveRaceCarState | None:
        return next((car for car in self.cars if car.id == car_id), None)

    def _should_attack(
        self,
        follower: LiveRaceCarState,
        ahead: LiveRaceCarState,
        distance_gap: float,
    ) -> bool:
        if distance_gap > ATTACK_WINDOW_METERS:
            return False

        segment = self._effective_segment(follower)
        overtake_chance = float(segment.overtake_chance)
        if segment.type == TrackSegmentType.LOW_SPEED_CORNER and overtake_chance < 0.10:
            return False
        if segment.type == TrackSegmentType.STRAIGHT:
            overtake_chance += 0.18
        elif segment.type == TrackSegmentType.HIGH_SPEED_CORNER:
            overtake_chance += 0.03
        else:
            overtake_chance -= 0.08

        speed_delta = max(-10.0, min(10.0, follower.current_speed_mps - ahead.current_speed_mps))
        confidence_bonus = (follower.confidence - 50.0) / 250.0
        tire_bonus = (follower.tire_condition - ahead.tire_condition) / 350.0
        grid_protection = 0.0
        if (
            ahead.grid_position < follower.grid_position
            and distance_gap < GRID_POSITION_HOLD_METERS
        ):
            grid_protection = 0.10
        chance = max(
            0.02,
            min(
                0.72,
                overtake_chance
                + speed_delta * 0.025
                + confidence_bonus
                + tire_bonus
                - grid_protection,
            ),
        )
        return self.rng.random() < chance

    def _should_complete_overtake(
        self,
        follower: LiveRaceCarState,
        ahead: LiveRaceCarState,
        distance_gap: float,
    ) -> bool:
        if distance_gap > OVERTAKE_RANGE_METERS:
            return False

        advantage = (
            (follower.current_speed_mps - ahead.current_speed_mps) * 0.06
            + (follower.confidence - ahead.confidence) * 0.003
            + (follower.tire_condition - ahead.tire_condition) * 0.002
        )
        chance = max(0.08, min(0.70, 0.30 + advantage))
        return self.rng.random() < chance

    def _apply_tire_wear(
        self, car: LiveRaceCarState, distance: float, segment: TrackSegmentSnapshot
    ) -> None:
        actual_wear = tire_wear_for_distance(
            car.tire_compound,
            distance,
            track_temperature_c=self.track_temp,
            wetness=self._current_wetness(car),
            high_speed_corner_share=(
                1.0 if segment.type == TrackSegmentType.HIGH_SPEED_CORNER else 0.0
            ),
        )
        car.tire_condition = max(0.0, car.tire_condition - actual_wear)

    def _check_for_dnf(self, car: LiveRaceCarState) -> bool:
        chance = max(0.0, (100.0 - car.reliability) / 100.0) * 0.00035
        if self._effective_condition(car) == CarCondition.DAMAGED:
            chance *= 1.4
        if self.rng.random() < chance:
            car.status = "DNF"
            car.dnf_reason = "Техническая неисправность"
            car.resulting_condition = self._dnf_damage_condition(car, technical=True)
            car.confidence = max(0.0, car.confidence - 20.0)
            return True
        return False

    def _dnf_damage_condition(self, car: LiveRaceCarState, *, technical: bool) -> CarCondition:
        heavy_probability = 0.20 if technical else 0.35
        if self._effective_condition(car) == CarCondition.DAMAGED:
            heavy_probability += 0.20
        return (
            CarCondition.HEAVILY_DAMAGED
            if self.rng.random() < heavy_probability
            else CarCondition.DAMAGED
        )

    def _apply_minor_damage(self, car: LiveRaceCarState) -> None:
        if self._effective_condition(car) == CarCondition.DAMAGED and self.rng.random() < 0.35:
            car.resulting_condition = CarCondition.HEAVILY_DAMAGED
        elif self._effective_condition(car) != CarCondition.HEAVILY_DAMAGED:
            car.resulting_condition = CarCondition.DAMAGED

    def _check_for_incidents(
        self,
        car: LiveRaceCarState,
        segment: TrackSegmentSnapshot,
    ) -> str | None:
        base_crash_chance = 0.0001
        if segment.type in (TrackSegmentType.LOW_SPEED_CORNER, TrackSegmentType.HIGH_SPEED_CORNER):
            base_crash_chance *= 3.0

        compound = TIRE_COMPOUNDS.get(car.tire_compound, TIRE_COMPOUNDS["Medium"])
        local_wetness = self._current_wetness(car)
        if compound.name in ("Soft", "Medium", "Hard") and local_wetness > 0.05:
            base_crash_chance *= 1.0 + local_wetness * 10.0

        if car.tire_condition < 30.0:
            base_crash_chance *= 4.0

        # Stage 5: Confidence impact
        if car.confidence < 30.0:
            base_crash_chance *= 2.0

        if self._effective_condition(car) == CarCondition.DAMAGED:
            base_crash_chance *= 2.0
        elif self._effective_condition(car) == CarCondition.HEAVILY_DAMAGED:
            base_crash_chance *= 4.0

        if self.rng.random() < base_crash_chance:
            severity = self.rng.random()
            if severity < 0.6:
                # Lock-up
                car.tire_condition = max(0.0, car.tire_condition - 5.0)
                self._set_total_distance(car, self._total_distance(car) - 20.0)
                car.confidence = max(0.0, car.confidence - 5.0)
                return "Блокировка колёс в повороте"
            elif severity < 0.9:
                # Minor damage
                car.tire_condition = max(0.0, car.tire_condition - 10.0)
                self._set_total_distance(car, self._total_distance(car) - 50.0)
                car.confidence = max(0.0, car.confidence - 10.0)
                self._apply_minor_damage(car)
                return "Лёгкий контакт"
            else:
                # Major crash: DNF
                car.status = "DNF"
                car.dnf_reason = "Авария"
                car.resulting_condition = self._dnf_damage_condition(car, technical=False)
                car.confidence = max(0.0, car.confidence - 20.0)
                return "Серьёзная авария"
        return None

    def _condition_multiplier(self, car: LiveRaceCarState) -> float:
        if self._effective_condition(car) == CarCondition.HEAVILY_DAMAGED:
            return 0.75
        if self._effective_condition(car) == CarCondition.DAMAGED:
            return 0.88
        return 1.0

    def _effective_condition(self, car: LiveRaceCarState) -> CarCondition:
        return car.resulting_condition or car.condition

    def _advance_pit_lane_cars(self, tick_start_time: float) -> None:
        for car in self.cars:
            if car.status == "IN_PITS":
                self._advance_pit_lane_car(car, tick_start_time)

    def _initialize_pit_phase(self, car: LiveRaceCarState) -> None:
        if car.pit_service_duration_seconds is None:
            car.pit_service_duration_seconds = self._assign_pit_service_duration()
        if car.pit_phase is not None:
            return
        if self._total_distance(car) >= self._pit_service_distance(car):
            car.pit_phase = "SERVICE"
            self._start_pit_service(car, car.pit_entry_time or self.race_time)
        else:
            car.pit_phase = "ENTRY"
        if car.pit_entry_time is None:
            car.pit_entry_time = self.race_time
            car.pit_available_from = self.race_time
            car.pit_exit_time = None

    def _pit_service_distance(self, car: LiveRaceCarState) -> float:
        return car.lap * self.track_length_meters + PIT_SERVICE_POINT

    def _pit_exit_distance(self, car: LiveRaceCarState) -> float:
        return car.lap * self.track_length_meters + PIT_LANE_LENGTH

    def _advance_pit_lane_car(self, car: LiveRaceCarState, tick_start_time: float) -> None:
        self._initialize_pit_phase(car)
        current_time = max(tick_start_time, car.pit_available_from)
        remaining = max(0.0, tick_start_time + self.tick_game_seconds - current_time)
        while remaining > 1e-9 and car.status == "IN_PITS":
            if car.pit_phase == "ENTRY":
                seconds = min(
                    remaining,
                    max(0.0, self._pit_service_distance(car) - self._total_distance(car))
                    / PIT_LANE_SPEED,
                )
                self._set_total_distance(car, self._total_distance(car) + PIT_LANE_SPEED * seconds)
                car.current_speed_mps = PIT_LANE_SPEED
                current_time += seconds
                remaining -= seconds
                if self._total_distance(car) >= self._pit_service_distance(car) - 1e-9:
                    car.pit_phase = "SERVICE"
                    self._start_pit_service(car, current_time)
                continue
            if car.pit_phase == "SERVICE":
                duration = car.pit_service_duration_seconds
                assert duration is not None
                seconds = min(remaining, max(0.0, duration - car.pit_service_elapsed_seconds))
                car.pit_service_elapsed_seconds += seconds
                car.pit_timer = car.pit_service_elapsed_seconds
                car.current_speed_mps = 0.0
                current_time += seconds
                remaining -= seconds
                if car.pit_service_elapsed_seconds >= duration - 1e-9:
                    car.pit_phase = "EXIT"
                    car.pit_service_release_time = current_time
                continue
            if car.pit_phase == "EXIT":
                seconds = min(
                    remaining,
                    max(0.0, self._pit_exit_distance(car) - self._total_distance(car))
                    / PIT_LANE_SPEED,
                )
                self._set_total_distance(car, self._total_distance(car) + PIT_LANE_SPEED * seconds)
                car.current_speed_mps = PIT_LANE_SPEED
                current_time += seconds
                remaining -= seconds
                if self._total_distance(car) >= self._pit_exit_distance(car) - 1e-9:
                    self._finish_pit_exit(car, current_time)
                continue
            raise ValueError(f"Unknown pit phase: {car.pit_phase}")

        if car.status == "IN_PITS":
            car.pit_waiting_seconds = 0.0

    def _start_pit_service(self, car: LiveRaceCarState, event_time: float) -> None:
        if car.pit_service_duration_seconds is None:
            car.pit_service_duration_seconds = self._assign_pit_service_duration()
        car.pit_service_elapsed_seconds = min(
            car.pit_service_elapsed_seconds, car.pit_service_duration_seconds
        )
        car.pit_timer = car.pit_service_elapsed_seconds
        car.pit_service_start_time = event_time
        if car.target_tire_compound:
            previous_compound = car.tire_compound
            car.tire_compound = car.target_tire_compound
            car.used_tire_compounds.append(car.tire_compound)
            if previous_compound != car.tire_compound and bool(
                {previous_compound, car.tire_compound} & WET_WEATHER_COMPOUNDS
            ):
                car.last_weather_tire_change_lap = car.lap
            if car.target_strategy_stint_index is not None:
                car.strategy_stint_index = car.target_strategy_stint_index
            car.target_strategy_stint_index = None
            car.tire_condition = 100.0
            car.target_tire_compound = None
            car.cliff_triggered = False

    def _assign_pit_service_duration(self) -> float:
        """Draw one stable, seeded duration for this pit stop."""
        category_roll = self.rng.random()
        range_roll = self.rng.random()
        if category_roll < 0.80:
            return 2.2 + 0.8 * range_roll
        if category_roll < 0.97:
            return 3.1 + 1.7 * range_roll
        return 5.0 + 4.0 * range_roll

    def _finish_cars_at_race_distance(self) -> None:
        race_distance = self.total_laps * self.track_length_meters
        for car in self.cars:
            if (
                car.status != "DNF"
                and car.status != "FINISHED"
                and car.absolute_distance is not None
                and car.absolute_distance >= race_distance
            ):
                self._mark_finished(
                    car,
                    finish_time=car.finish_time or self.race_time,
                    classified_laps=self.total_laps,
                )

    def _finish_pit_exit(self, car: LiveRaceCarState, event_time: float) -> None:
        if car.pit_entry_time is None:
            car.pit_entry_time = event_time
        car.pit_exit_time = event_time
        car.status = "RACING"
        car.pit_phase = None
        car.current_speed_mps = PIT_LANE_SPEED

    def _set_car_distance_on_current_lap(
        self,
        car: LiveRaceCarState,
        distance: float,
        *,
        update_absolute: bool = True,
    ) -> None:
        bounded = max(0.0, min(distance, self.track_length_meters))
        for segment in self.segments:
            start = self._segment_offsets[segment.id]
            end = start + float(segment.length_meters)
            if bounded <= end or segment.id == self.segments[-1].id:
                car.current_segment_id = segment.id
                car.progress = max(0.0, bounded - start)
                if update_absolute:
                    car.absolute_distance = car.lap * self.track_length_meters + bounded
                return

    def _set_total_distance(
        self,
        car: LiveRaceCarState,
        total_distance: float,
        *,
        allow_beyond_finish: bool = False,
    ) -> None:
        race_distance = self.total_laps * self.track_length_meters
        bounded = max(
            -self._grid_max_depth_meters(),
            total_distance if allow_beyond_finish else min(total_distance, race_distance),
        )
        car.absolute_distance = bounded

        if bounded < 0.0:
            car.lap = 0
            self._set_car_distance_on_current_lap(
                car,
                self.track_length_meters + bounded,
                update_absolute=False,
            )
            return

        if allow_beyond_finish and bounded >= race_distance:
            car.lap = self.total_laps
            self._set_car_distance_on_current_lap(
                car,
                bounded % self.track_length_meters,
                update_absolute=False,
            )
            return

        car.lap, distance_on_lap = self._lap_and_distance_on_lap(bounded)
        if car.lap >= self.total_laps:
            self._mark_finished(
                car,
                finish_time=car.finish_time or self.race_time,
                classified_laps=self.total_laps,
            )
            return
        self._set_car_distance_on_current_lap(
            car,
            distance_on_lap,
            update_absolute=False,
        )

    def _mark_finished(
        self,
        car: LiveRaceCarState,
        *,
        finish_time: float,
        classified_laps: int,
    ) -> None:
        car.status = "FINISHED"
        car.finish_time = finish_time
        car.classified_laps = max(0, min(classified_laps, self.total_laps))
        car.lap = car.classified_laps
        if car.id not in self._finish_order:
            self._finish_order.append(car.id)

    def _next_segment_id(self, segment_id: int) -> int:
        for index, segment in enumerate(self.segments):
            if segment.id == segment_id:
                return self.segments[(index + 1) % len(self.segments)].id
        raise ValueError(f"Unknown track segment id: {segment_id}")

    def get_final_results(self, cars_map: dict[str, Car]) -> list[RaceSimulationResult]:
        if any(car.status not in ("FINISHED", "DNF") for car in self.cars):
            return []

        ranked = self._ranked_cars()
        classified = [
            car for car in ranked if car.status == "FINISHED" and self._dry_tire_rule_satisfied(car)
        ]
        disqualified = [
            car
            for car in ranked
            if car.status == "FINISHED" and not self._dry_tire_rule_satisfied(car)
        ]
        retired = [car for car in ranked if car.status == "DNF"]
        ranked = [*classified, *retired, *disqualified]
        results = []

        for pos, car_state in enumerate(ranked, start=1):
            car_model = cars_map.get(car_state.id)
            if not car_model:
                continue

            if car_state.status == "DNF":
                status = ResultStatus.DNF
            elif not self._dry_tire_rule_satisfied(car_state):
                status = ResultStatus.DISQUALIFIED
            else:
                status = ResultStatus.CLASSIFIED
            points = F1_POINTS_BY_POSITION.get(pos, 0) if status == ResultStatus.CLASSIFIED else 0
            reason = (
                "Не использованы две разные спецификации сухих шин"
                if status == ResultStatus.DISQUALIFIED
                else car_state.dnf_reason
            )

            results.append(
                RaceSimulationResult(
                    car=car_model,
                    grid_position=car_state.grid_position,
                    finish_position=pos,
                    best_lap=self._format_lap_time(car_state.personal_best_lap_time_ms),
                    best_lap_number=car_state.personal_best_lap_number,
                    max_speed_kph=round(car_state.max_speed_kph, 3),
                    gap=(
                        "Дисквалифицирован"
                        if status == ResultStatus.DISQUALIFIED
                        else self._format_final_gap(car_state, ranked[0], pos)
                    ),
                    laps=(
                        car_state.classified_laps
                        if status == ResultStatus.CLASSIFIED
                        and car_state.classified_laps is not None
                        else car_state.lap
                    ),
                    points=points,
                    status=status,
                    event=car_state.event_type,
                    reason=reason,
                    event_description=(f"{car_state.pilot_name}: {reason or 'гонка завершена'}"),
                    event_severity=(
                        EventSeverity.CRITICAL
                        if status in (ResultStatus.DNF, ResultStatus.DISQUALIFIED)
                        else EventSeverity.INFO
                    ),
                    resulting_condition=car_state.resulting_condition,
                )
            )
        return results

    @staticmethod
    def _format_lap_time(lap_time_ms: int | None) -> str | None:
        if lap_time_ms is None:
            return None
        minutes, remainder = divmod(lap_time_ms, 60_000)
        seconds, milliseconds = divmod(remainder, 1_000)
        return f"{minutes}:{seconds:02d}.{milliseconds:03d}"

    def _format_final_gap(self, car: LiveRaceCarState, leader: LiveRaceCarState, pos: int) -> str:
        if car.status == "DNF":
            return "Сход"
        if pos == 1:
            return "Лидер"

        lap_gap = self._classified_lap_gap(car, leader)
        if lap_gap == 1:
            return "+1 круг"
        if lap_gap > 1:
            return f"+{lap_gap} кругов"

        if car.finish_time is None or leader.finish_time is None:
            return "Сход"
        gap = max(0.0, car.finish_time - leader.finish_time)
        return f"+{gap:.3f}с"

    def _classified_lap_gap(self, car: LiveRaceCarState, leader: LiveRaceCarState) -> int:
        leader_laps = leader.classified_laps if leader.classified_laps is not None else leader.lap
        car_laps = car.classified_laps if car.classified_laps is not None else car.lap
        return max(0, leader_laps - car_laps)

    def _total_distance(self, car: LiveRaceCarState) -> float:
        if car.status == "DNF":
            return -1.0
        if car.absolute_distance is not None:
            return car.absolute_distance
        return (
            car.lap * self.track_length_meters
            + self._segment_offsets[car.current_segment_id]
            + car.progress
        )

    def _ranked_cars(self) -> list[LiveRaceCarState]:
        classified = [c for c in self.cars if c.status != "DNF"]
        dnfs = [c for c in self.cars if c.status == "DNF"]

        if all(car.status == "FINISHED" for car in classified):
            sorted_classified = sorted(
                classified,
                key=lambda car: (
                    -(car.classified_laps if car.classified_laps is not None else car.lap),
                    car.finish_time if car.finish_time is not None else float("inf"),
                    (
                        self._finish_order.index(car.id)
                        if car.id in self._finish_order
                        else len(self._finish_order)
                    ),
                    car.grid_position,
                ),
            )
        else:
            sorted_classified = sorted(
                classified,
                key=lambda car: (
                    -self._total_distance(car),
                    (
                        self._finish_order.index(car.id)
                        if car.id in self._finish_order
                        else len(self._finish_order)
                    ),
                    car.grid_position,
                ),
            )

        # DNF cars stay below classified runners.
        sorted_dnfs = sorted(
            dnfs,
            key=lambda car: (
                -(car.classified_laps if car.classified_laps is not None else car.lap),
                car.pilot_name,
            ),
        )

        return sorted_classified + sorted_dnfs

    def _build_segment_offsets(self) -> dict[int, float]:
        offsets: dict[int, float] = {}
        distance = 0.0
        for segment in self.segments:
            offsets[segment.id] = distance
            distance += float(segment.length_meters)
        return offsets

    def _race_variance_multiplier(self, car: LiveRaceCarState) -> float:
        if len(self.cars) < 2 or self.tick_id == 0:
            return 1.0
        phase = self._race_phase_by_car_id.get(car.id, 0.0)
        wave = 0.004 * self._wave(self.tick_id / 11.0 + phase)
        return 1.0 + self._race_bias_by_car_id.get(car.id, 0.0) + wave

    def _traffic_speed_multiplier(
        self,
        car: LiveRaceCarState,
        segment: TrackSegmentSnapshot,
    ) -> float:
        if self.tick_id == 0:
            return 1.0
        _, gap = self._nearest_racing_car_ahead(car)
        if gap is None or gap <= 0.0 or gap > DIRTY_AIR_RANGE_METERS:
            return 1.0

        if (
            segment.type == TrackSegmentType.STRAIGHT
            and float(segment.overtake_chance) >= 0.24
            and gap <= ATTACK_WINDOW_METERS
        ):
            return 1.0 + SLIPSTREAM_BONUS

        closeness = 1.0 - gap / DIRTY_AIR_RANGE_METERS
        penalty = DIRTY_AIR_MAX_PENALTY * max(0.0, closeness)
        if segment.type == TrackSegmentType.HIGH_SPEED_CORNER:
            penalty *= 1.25
        elif segment.type == TrackSegmentType.LOW_SPEED_CORNER:
            penalty *= 0.7
        return max(0.88, 1.0 - penalty)

    def _nearest_racing_car_ahead(
        self,
        car: LiveRaceCarState,
    ) -> tuple[LiveRaceCarState | None, float | None]:
        own_distance = self._total_distance(car)
        nearest_car = None
        nearest_gap = None
        for candidate in self.cars:
            if candidate.id == car.id or candidate.status not in ("RACING", "PIT_REQUESTED"):
                continue
            gap = self._total_distance(candidate) - own_distance
            if gap <= 0:
                continue
            if nearest_gap is None or gap < nearest_gap:
                nearest_car = candidate
                nearest_gap = gap
        return nearest_car, nearest_gap

    def _stable_signed_fraction(self, value: str) -> float:
        digest = sha256(value.encode("utf-8")).hexdigest()
        number = int(digest[:8], 16) / 0xFFFFFFFF
        return number * 2.0 - 1.0

    def _wave(self, value: float) -> float:
        wrapped = value % 1.0
        return 1.0 - abs(wrapped * 4.0 - 2.0)
