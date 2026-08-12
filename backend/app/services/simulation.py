from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from app.domain.constants import F1_POINTS_BY_POSITION
from app.domain.enums import (
    CarCondition,
    EventSeverity,
    PracticeSegment,
    RaceEventType,
    ResultStatus,
    SessionType,
    TrackProfile,
    TrackSegmentType,
)
from app.models import Car, CarSetup, SeasonStage, SessionResult
from app.services.text_content import build_practice_report, ideal_setup_targets
from app.services.weather import build_weather_payload


def _track_profile(track) -> TrackProfile:
    if not track.segments:
        return TrackProfile.BALANCED
    corner_length = sum(
        float(segment.length_meters)
        for segment in track.segments
        if segment.type != TrackSegmentType.STRAIGHT
    )
    corner_ratio = corner_length / float(track.track_length_meters)
    if corner_ratio < 0.35:
        return TrackProfile.SPEED
    if corner_ratio > 0.62:
        return TrackProfile.TECHNICAL
    return TrackProfile.BALANCED


@dataclass(frozen=True)
class SimulationMetric:
    car: Car
    score: float
    risk: float
    setup_gap: int
    seed: int


@dataclass(frozen=True)
class PracticeSimulationResult:
    car: Car
    position: int
    best_lap: str
    gap: str
    laps: int
    status: ResultStatus
    event: RaceEventType | None
    reason: str | None
    setup_feedback: str
    engineer_recommendation: str


@dataclass(frozen=True)
class QualifyingSimulationResult:
    car: Car
    position: int
    best_lap: str | None
    gap: str
    laps: int
    status: ResultStatus
    event: RaceEventType | None
    reason: str | None


@dataclass(frozen=True)
class RaceSimulationResult:
    car: Car
    grid_position: int
    finish_position: int
    best_lap: str | None
    gap: str
    laps: int
    points: int
    status: ResultStatus
    event: RaceEventType
    reason: str | None
    event_description: str
    event_severity: EventSeverity
    resulting_condition: CarCondition | None = None
    best_lap_number: int | None = None
    max_speed_kph: float | None = None


class SimpleSimulationService:
    """Small deterministic MVP simulation, seeded by persisted entity IDs."""

    def simulate_practice(
        self,
        stage: SeasonStage,
        cars: list[Car],
        setups: dict,
        segment: PracticeSegment = PracticeSegment.FP1,
    ) -> list[PracticeSimulationResult]:
        metrics = self._ranked_metrics(stage, cars, setups, SessionType.PRACTICE)
        lap_times = [
            self._lap_time(stage, metric, position, SessionType.PRACTICE)
            for position, metric in enumerate(metrics, start=1)
        ]
        results = []
        for position, (metric, best_lap) in enumerate(
            zip(metrics, lap_times, strict=False),
            start=1,
        ):
            setup = setups.get(metric.car.id)
            report = build_practice_report(
                profile=_track_profile(stage.track),
                wings_setting=setup.wings_setting if setup else metric.car.wings_setting,
                suspension_setting=(
                    setup.suspension_setting if setup else metric.car.suspension_setting
                ),
                gearbox_setting=setup.gearbox_setting if setup else metric.car.gearbox_setting,
                driver_id=metric.car.driver_id,
                stage_id=str(stage.id),
                segment=segment,
            )
            results.append(
                PracticeSimulationResult(
                    car=metric.car,
                    position=position,
                    best_lap=best_lap,
                    gap=self._timing_gap(best_lap, lap_times[0]),
                    laps=max(stage.track.laps // 3, 8),
                    status=ResultStatus.CLASSIFIED,
                    event=self._practice_event(metric),
                    reason=self._practice_reason(metric),
                    setup_feedback=report.setup_feedback,
                    engineer_recommendation=report.engineer_recommendation,
                )
            )
        return results

    def simulate_qualifying(
        self,
        stage: SeasonStage,
        cars: list[Car],
        setups: dict,
    ) -> list[QualifyingSimulationResult]:
        metrics = self._ranked_metrics(stage, cars, setups, SessionType.QUALIFYING)
        rows: list[QualifyingSimulationResult] = []
        classified_position = 1
        no_time_rows: list[tuple[SimulationMetric, str]] = []
        classified_metrics: list[SimulationMetric] = []

        for metric in metrics:
            no_time_reason = self._qualifying_no_time_reason(metric)
            if no_time_reason is not None:
                no_time_rows.append((metric, no_time_reason))
                continue
            classified_metrics.append(metric)
            classified_position += 1

        classified_lap_times = [
            self._lap_time(stage, metric, position, SessionType.QUALIFYING)
            for position, metric in enumerate(classified_metrics, start=1)
        ]

        for position, (metric, best_lap) in enumerate(
            zip(classified_metrics, classified_lap_times, strict=False),
            start=1,
        ):
            rows.append(
                QualifyingSimulationResult(
                    car=metric.car,
                    position=position,
                    best_lap=best_lap,
                    gap=self._timing_gap(best_lap, classified_lap_times[0]),
                    laps=6,
                    status=ResultStatus.CLASSIFIED,
                    event=None,
                    reason=None,
                )
            )

        classified_position = len(classified_metrics) + 1

        for metric, reason in no_time_rows:
            rows.append(
                QualifyingSimulationResult(
                    car=metric.car,
                    position=classified_position,
                    best_lap=None,
                    gap="Без времени",
                    laps=0,
                    status=ResultStatus.NO_TIME,
                    event=RaceEventType.NO_TIME,
                    reason=reason,
                )
            )
            classified_position += 1

        return rows

    def simulate_race(
        self,
        stage: SeasonStage,
        cars: list[Car],
        setups: dict,
        qualifying_results: list[SessionResult],
    ) -> list[RaceSimulationResult]:
        # 1. Build the qualifying grid. Component replacement penalties no longer exist.
        grid_by_car_id = {result.car_id: result.position for result in qualifying_results}
        actual_grid_by_car_id = {
            car.id: position
            for position, car in enumerate(
                sorted(
                    cars,
                    key=lambda car: (grid_by_car_id.get(car.id, len(cars)), car.driver_id),
                ),
                start=1,
            )
        }

        # 2. Run Metrics with actual grid bonus
        metrics = self._race_ranked_metrics(stage, cars, setups, actual_grid_by_car_id)
        classified: list[tuple[SimulationMetric, RaceEventType, str | None]] = []
        non_classified: list[tuple[SimulationMetric, RaceEventType, str]] = []

        for metric in metrics:
            event, reason = self._race_event(metric)
            if event == RaceEventType.DNF:
                non_classified.append((metric, event, reason or "Сход."))
            else:
                classified.append((metric, event, reason))

        rows: list[RaceSimulationResult] = []
        for finish_position, (metric, event, reason) in enumerate(classified, start=1):
            points = F1_POINTS_BY_POSITION.get(finish_position, 0)
            rows.append(
                RaceSimulationResult(
                    car=metric.car,
                    grid_position=actual_grid_by_car_id.get(metric.car.id, finish_position),
                    finish_position=finish_position,
                    best_lap=self._lap_time(stage, metric, finish_position, SessionType.RACE),
                    best_lap_number=None,
                    max_speed_kph=None,
                    gap=self._race_gap(finish_position),
                    laps=stage.track.laps,
                    points=points,
                    status=ResultStatus.CLASSIFIED,
                    event=event,
                    reason=reason,
                    event_description=self._race_event_description(event, metric, reason),
                    event_severity=self._event_severity(event),
                    resulting_condition=self._resulting_condition(metric, event, reason),
                )
            )

        for offset, (metric, event, reason) in enumerate(non_classified, start=1):
            finish_position = len(classified) + offset
            rows.append(
                RaceSimulationResult(
                    car=metric.car,
                    grid_position=actual_grid_by_car_id.get(metric.car.id, finish_position),
                    finish_position=finish_position,
                    best_lap=None,
                    best_lap_number=None,
                    max_speed_kph=None,
                    gap="Сход",
                    laps=max(stage.track.laps - 4 - offset, 0),
                    points=0,
                    status=ResultStatus.DNF,
                    event=event,
                    reason=reason,
                    event_description=self._race_event_description(event, metric, reason),
                    event_severity=self._event_severity(event),
                    resulting_condition=self._resulting_condition(metric, event, reason),
                )
            )
        return rows

    def _ranked_metrics(
        self,
        stage: SeasonStage,
        cars: list[Car],
        setups: dict,
        session_type: SessionType,
    ) -> list[SimulationMetric]:
        return sorted(
            [self._metric(stage, car, setups.get(car.id), session_type) for car in cars],
            key=lambda metric: (-metric.score, metric.risk, metric.car.driver_id),
        )

    def _race_ranked_metrics(
        self,
        stage: SeasonStage,
        cars: list[Car],
        setups: dict,
        grid_by_car_id: dict,
    ) -> list[SimulationMetric]:
        metrics = []
        for car in cars:
            metric = self._metric(stage, car, setups.get(car.id), SessionType.RACE)
            grid_position = grid_by_car_id.get(car.id, len(cars) + 1)
            grid_bonus = max(0, len(cars) + 1 - grid_position) * 1.5
            metrics.append(
                SimulationMetric(
                    car=metric.car,
                    score=metric.score + grid_bonus,
                    risk=metric.risk,
                    setup_gap=metric.setup_gap,
                    seed=metric.seed,
                )
            )
        return sorted(
            metrics,
            key=lambda metric: (-metric.score, metric.risk, metric.car.driver_id),
        )

    def _metric(
        self,
        stage: SeasonStage,
        car: Car,
        setup: CarSetup | None,
        session_type: SessionType,
    ) -> SimulationMetric:
        wings = setup.wings_setting if setup is not None else car.wings_setting
        suspension = setup.suspension_setting if setup is not None else car.suspension_setting
        gearbox = setup.gearbox_setting if setup is not None else car.gearbox_setting

        setup_gap = self._setup_gap_combined(stage, wings, suspension, gearbox)
        seed = self._seed(stage, car, session_type)

        # Stage 2: Performance score
        profile = _track_profile(stage.track)
        if profile == TrackProfile.SPEED:
            perf_score = (
                car.engine_power * 0.50 + car.aero_efficiency * 0.30 + car.chassis_grip * 0.20
            )
        elif profile == TrackProfile.TECHNICAL:
            perf_score = (
                car.chassis_grip * 0.50 + car.aero_efficiency * 0.30 + car.engine_power * 0.20
            )
        else:
            perf_score = (car.engine_power + car.aero_efficiency + car.chassis_grip) / 3.0

        # Stage 3 & 4: Reliability and Tire impact
        tire_score_mod = self._calculate_tire_score_modifier(stage, car, session_type)

        # Stage 5: Confidence Multiplier
        confidence_mod = 0.0
        if car.confidence >= 50:
            confidence_mod = ((car.confidence - 50) / 50) * 1.5  # +1.5%
        else:
            confidence_mod = -((50 - car.confidence) / 50) * 2.0  # -2.0%

        base_score = car.driver.pace * 0.45 + perf_score * 0.55
        score = (
            base_score
            + tire_score_mod
            + confidence_mod
            + self._setup_modifier(setup_gap)
            + self._condition_score_modifier(car)
            + self._jitter(seed)
        )

        # Reliability risk (Stage 4)
        reliability_risk = (100 - car.reliability) * 0.25

        # Stage 5: Confidence impact on risk
        psychology_risk = 0.0
        if car.confidence < 30:
            psychology_risk = (30 - car.confidence) * 2.0

        risk = (
            (100 - car.driver.stability) * 0.25
            + reliability_risk
            + psychology_risk
            + setup_gap * 0.20
            + self._weather_risk(stage, session_type)
            + self._condition_risk(car)
        )
        return SimulationMetric(
            car=car,
            score=score,
            risk=risk,
            setup_gap=int(setup_gap),
            seed=seed,
        )

    def _calculate_tire_score_modifier(
        self, stage: SeasonStage, car: Car, session_type: SessionType
    ) -> float:
        track_wetness = float(self._weather_snapshot(stage, session_type)["trackWetness"])

        compound = "Medium"
        if track_wetness > 0.5:
            compound = "Wet"
        elif track_wetness > 0.1:
            compound = "Intermediate"

        grips = {"Soft": 3.0, "Medium": 1.5, "Hard": 0.0, "Intermediate": -2.0, "Wet": -5.0}
        base_mod = grips.get(compound, 0.0)

        if compound in ("Soft", "Medium", "Hard") and track_wetness > 0.05:
            base_mod -= track_wetness * 50.0

        return base_mod

    def _setup_gap_combined(
        self,
        stage: SeasonStage,
        wings: int,
        suspension: int,
        gearbox: int,
    ) -> float:
        ideal_wings, ideal_susp, ideal_gear = ideal_setup_targets(_track_profile(stage.track))

        gap = (
            abs(wings - ideal_wings) + abs(suspension - ideal_susp) + abs(gearbox - ideal_gear)
        ) / 3.0
        return gap

    def _setup_modifier(self, setup_gap: float) -> float:
        if setup_gap <= 5:
            return 5.0
        if setup_gap <= 15:
            return 0.0
        if setup_gap <= 30:
            return -5.0
        return -12.0

    def _weather_risk(self, stage: SeasonStage, session_type: SessionType) -> float:
        wetness = float(self._weather_snapshot(stage, session_type)["trackWetness"])
        return wetness * 22.0

    def _weather_snapshot(self, stage: SeasonStage, session_type: SessionType) -> dict:
        weather = build_weather_payload(stage.weather_scenario)
        if session_type == SessionType.QUALIFYING:
            return weather["qualifying"]
        if session_type == SessionType.RACE:
            forecast = weather["raceForecast"][0]
            return {
                **forecast,
                "trackWetness": (
                    float(forecast["trackWetnessMin"]) + float(forecast["trackWetnessMax"])
                )
                / 2,
            }
        if stage.fp1_status.value == "available":
            return weather["practice"]["fp1"]
        if stage.fp2_status.value == "available":
            return weather["practice"]["fp2"]
        return weather["practice"]["fp3"]

    def _condition_score_modifier(self, car: Car) -> float:
        if car.condition == CarCondition.HEAVILY_DAMAGED:
            return -25.0
        if car.condition == CarCondition.DAMAGED:
            return -12.0
        return 0.0

    def _condition_risk(self, car: Car) -> float:
        if car.condition == CarCondition.HEAVILY_DAMAGED:
            return 35.0
        if car.condition == CarCondition.DAMAGED:
            return 18.0
        return 0.0

    def _qualifying_no_time_reason(self, metric: SimulationMetric) -> str | None:
        roll = metric.seed % 1000
        if metric.risk >= 75 or roll < metric.risk * 1.1:
            if metric.setup_gap > 25:
                return (
                    "Не удалось показать быстрый круг: настройки слишком далеки от оптимума трассы."
                )
            if getattr(metric.car, "reliability", 100) < 40:
                return "В квалификации не удалось показать время из-за технической проблемы."
            return "В квалификации не удалось показать время после ошибки пилота под давлением."
        return None

    def _race_event(self, metric: SimulationMetric) -> tuple[RaceEventType, str | None]:
        roll = (metric.seed // 1000) % 1000
        if metric.risk >= 82 or roll < metric.risk * 0.55:
            if metric.car.reliability < 55:
                return RaceEventType.DNF, "Сход из-за технической неисправности."
            if metric.setup_gap > 25:
                return RaceEventType.DNF, "Сход после серьёзной аварии на нестабильной машине."
            return (
                RaceEventType.DNF,
                "Сход после инцидента на трассе.",
            )
        if metric.risk >= 62 or roll < metric.risk * 0.9:
            if metric.setup_gap > 25:
                return (
                    RaceEventType.DAMAGE,
                    "Машина получила повреждения из-за нестабильного поведения на этих настройках.",
                )
            return RaceEventType.DAMAGE, "Машина получила небольшие повреждения по ходу гонки."
        if metric.risk >= 40 or roll < metric.risk * 1.4:
            return RaceEventType.DRIVER_MISTAKE, "Потеря времени после ошибки пилота."
        return RaceEventType.CLEAN_RACE, None

    def _resulting_condition(
        self,
        metric: SimulationMetric,
        event: RaceEventType,
        reason: str | None,
    ) -> CarCondition | None:
        if event not in {RaceEventType.DAMAGE, RaceEventType.DNF}:
            return None

        roll = (metric.seed // 17) % 100
        if event == RaceEventType.DAMAGE:
            # A repeat contact can turn a minor repair into a heavy one.
            if metric.car.condition == CarCondition.DAMAGED and roll < 35:
                return CarCondition.HEAVILY_DAMAGED
            return CarCondition.DAMAGED

        reason_text = (reason or "").lower()
        heavy_threshold = 35  # Base DNF split: roughly 65% damaged / 35% heavy.
        if "техничес" in reason_text:
            heavy_threshold = 20
        elif "серьёзной аварии" in reason_text:
            heavy_threshold = 60
        if metric.car.condition == CarCondition.DAMAGED:
            heavy_threshold = min(90, heavy_threshold + 20)
        return CarCondition.HEAVILY_DAMAGED if roll < heavy_threshold else CarCondition.DAMAGED

    def _practice_event(self, metric: SimulationMetric) -> RaceEventType | None:
        if metric.setup_gap > 25:
            return RaceEventType.DRIVER_MISTAKE
        if metric.risk > 55:
            return RaceEventType.TECHNICAL_ISSUE
        return RaceEventType.CLEAN_RACE

    def _practice_reason(self, metric: SimulationMetric) -> str | None:
        if metric.setup_gap > 25:
            return "Темп на практике был ограничен неудачными настройками."
        if metric.risk > 55:
            return "Сессию на практике пришлось провести осторожно из-за повышенного риска."
        return None

    def _race_event_description(
        self,
        event: RaceEventType,
        metric: SimulationMetric,
        reason: str | None,
    ) -> str:
        driver_code = metric.car.driver.code
        if event == RaceEventType.CLEAN_RACE:
            return f"{driver_code} провёл чистую гонку в стабильном темпе."
        return f"{driver_code}: {reason}"

    def _event_severity(self, event: RaceEventType) -> EventSeverity:
        if event == RaceEventType.DNF:
            return EventSeverity.CRITICAL
        if event in {RaceEventType.DAMAGE, RaceEventType.TECHNICAL_ISSUE}:
            return EventSeverity.WARNING
        return EventSeverity.INFO

    def _lap_time(
        self,
        stage: SeasonStage,
        metric: SimulationMetric,
        position: int,
        session_type: SessionType,
    ) -> str:
        if stage.track.segments:
            base_lap_seconds = sum(
                float(segment.length_meters) / max(1.0, float(segment.base_speed))
                for segment in stage.track.segments
            )
        else:
            base_lap_seconds = float(stage.track.track_length_meters) / 55.0

        profile = _track_profile(stage.track)
        if profile == TrackProfile.SPEED:
            car_rating = (
                metric.car.engine_power * 0.50
                + metric.car.aero_efficiency * 0.30
                + metric.car.chassis_grip * 0.20
            )
        elif profile == TrackProfile.TECHNICAL:
            car_rating = (
                metric.car.chassis_grip * 0.50
                + metric.car.aero_efficiency * 0.30
                + metric.car.engine_power * 0.20
            )
        else:
            car_rating = (
                metric.car.engine_power + metric.car.aero_efficiency + metric.car.chassis_grip
            ) / 3.0

        session_multiplier = {
            SessionType.PRACTICE: 1.03,
            SessionType.QUALIFYING: 0.995,
            SessionType.RACE: 1.0,
        }[session_type]
        car_multiplier = 1.0 - (car_rating - 75.0) * 0.0018
        driver_multiplier = 1.0 - (metric.car.driver.pace - 75.0) * 0.0015
        setup_multiplier = 1.0 + metric.setup_gap * 0.0018

        weather = self._weather_snapshot(stage, session_type)
        wetness = float(weather.get("trackWetness", 0.0))
        compound_multiplier = 1.0
        if wetness > 0.5:
            compound_multiplier = 1.025
        elif wetness > 0.1:
            compound_multiplier = 1.012
        weather_multiplier = 1.0 + wetness * 0.04
        condition_multiplier = {
            CarCondition.HEALTHY: 1.0,
            CarCondition.DAMAGED: 1.022,
            CarCondition.HEAVILY_DAMAGED: 1.07,
        }[metric.car.condition]
        jitter_seconds = ((metric.seed % 401) / 400.0 - 0.5) * (
            0.16 if session_type == SessionType.PRACTICE else 0.08
        )
        position_spread_seconds = max(0, position - 1) * 0.10
        total_seconds = (
            base_lap_seconds
            * session_multiplier
            * car_multiplier
            * driver_multiplier
            * setup_multiplier
            * compound_multiplier
            * weather_multiplier
            * condition_multiplier
            + jitter_seconds
            + position_spread_seconds
        )
        total_millis = max(1, round(total_seconds * 1000))
        minutes = total_millis // 60_000
        seconds = (total_millis % 60_000) // 1000
        millis = total_millis % 1000
        return f"{minutes}:{seconds:02d}.{millis:03d}"

    def _parse_lap_time_millis(self, lap_time: str | None) -> int | None:
        if lap_time is None:
            return None
        minutes_part, seconds_part = lap_time.split(":", maxsplit=1)
        seconds, millis = seconds_part.split(".", maxsplit=1)
        return int(minutes_part) * 60_000 + int(seconds) * 1000 + int(millis)

    def _format_gap_millis(self, gap_millis: int | None) -> str:
        if gap_millis is None:
            return "Без времени"
        if gap_millis <= 0:
            return "Лидер"
        return f"+{gap_millis / 1000:.3f}с"

    def _timing_gap(self, lap_time: str | None, leader_lap_time: str | None) -> str:
        lap_millis = self._parse_lap_time_millis(lap_time)
        leader_millis = self._parse_lap_time_millis(leader_lap_time)
        if lap_millis is None or leader_millis is None:
            return self._format_gap_millis(None)
        return self._format_gap_millis(lap_millis - leader_millis)

    def _race_gap(self, position: int) -> str:
        if position == 1:
            return "Лидер"
        return f"+{(position - 1) * 4.250:.3f}с"

    def _seed(self, stage: SeasonStage, car: Car, session_type: SessionType) -> int:
        raw_seed = f"{stage.season_id}:{stage.id}:{session_type.value}:{car.id}".encode()
        return int.from_bytes(sha256(raw_seed).digest()[:8], byteorder="big")

    def _jitter(self, seed: int) -> float:
        return (seed % 401) / 100 - 2.0
