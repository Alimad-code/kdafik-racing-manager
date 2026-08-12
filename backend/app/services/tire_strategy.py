from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.models import Track
from app.services.pit_lane import (
    EXPECTED_PIT_SERVICE_SECONDS,
    PIT_LANE_LENGTH_METERS,
    PIT_LANE_SPEED_MPS,
)
from app.services.tires import (
    SLICK_COMPOUNDS,
    TIRE_COMPOUNDS,
    WET_WEATHER_COMPOUNDS,
    dry_tire_rule_satisfied,
    tire_grip_multiplier,
    tire_wear_for_distance,
)
from app.services.weather import (
    build_race_keyframes,
    climate_from_track,
    race_weather_at,
    update_track_wetness,
)

MIN_END_CONDITION = 32.0
DP_PATHS_PER_STATE = 1
SHORT_STINT_IDEAL_SHARE = 0.10
USEFUL_SHORT_STINT_PIT_LOSS_FRACTION = 0.35
INTERMEDIATE_MIN_WETNESS = 0.10
INTERMEDIATE_MIN_RAIN = 0.30
WET_MIN_WETNESS = 0.50
WET_MIN_RAIN = 0.55

_SLICK_BITS = {"Soft": 1, "Medium": 2, "Hard": 4}


@dataclass(frozen=True)
class StrategyStint:
    compound: str
    start_lap: int
    end_lap: int
    pit_window_start_lap: int | None = None
    pit_window_end_lap: int | None = None


@dataclass(frozen=True)
class TireStrategy:
    number: int
    pit_stop_count: int
    stints: tuple[StrategyStint, ...]
    estimated_time: float


@dataclass(frozen=True)
class _StintCost:
    compound: str
    start_lap: int
    end_lap: int
    end_condition: float
    seconds: float


@dataclass(frozen=True)
class _Path:
    seconds: float
    stints: tuple[_StintCost, ...]
    slick_mask: int
    used_wet_weather_tire: bool


def build_tire_strategies(
    track: Track,
    weather_payload: dict[str, Any],
) -> list[TireStrategy] | None:
    """Return the three fastest unique plans, prioritizing competitive options."""
    lap_weather = _weather_by_lap(track.laps, weather_payload["raceForecast"])
    candidates = _dynamic_programming_candidates(track, lap_weather)
    if not candidates:
        return None

    unique: dict[tuple[tuple[str, int, int], ...], TireStrategy] = {}
    for candidate in sorted(candidates, key=lambda item: (item.estimated_time, _signature(item))):
        unique.setdefault(_signature(candidate), candidate)

    ordered = sorted(unique.values(), key=lambda item: (item.estimated_time, _signature(item)))
    competitive_limit = ordered[0].estimated_time + pit_loss_seconds(track)
    competitive = [
        candidate for candidate in ordered if candidate.estimated_time <= competitive_limit + 1e-9
    ]
    selected = [*competitive]
    if len(selected) < 3:
        existing = {_signature(candidate) for candidate in selected}
        selected.extend(candidate for candidate in ordered if _signature(candidate) not in existing)
    selected = selected[:3]
    if len(selected) < 3:
        return None

    return [
        TireStrategy(
            number=index,
            pit_stop_count=candidate.pit_stop_count,
            stints=candidate.stints,
            estimated_time=candidate.estimated_time,
        )
        for index, candidate in enumerate(selected, start=1)
    ]


def pit_loss_seconds(track: Track) -> float:
    average_overtake = _average_overtake_chance(track)
    raw_loss = PIT_LANE_LENGTH_METERS / PIT_LANE_SPEED_MPS + EXPECTED_PIT_SERVICE_SECONDS
    return raw_loss * (1.08 - 0.16 * average_overtake)


def weather_starting_compound(
    track: Track,
    weather_payload: dict[str, Any],
    weather_scenario: dict[str, Any] | None = None,
) -> str | None:
    """Predict the surface after two laps and return only a weather override."""
    if weather_scenario:
        return _simulated_weather_starting_compound(track, weather_scenario)

    lap_weather = _weather_by_lap(track.laps, weather_payload["raceForecast"])
    horizon = lap_weather[: min(3, len(lap_weather))]
    if not horizon:
        return None

    wetness = [float(item["wetness"]) for item in horizon]
    rain = [float(item["rain"]) for item in horizon]
    average_wetness = sum(wetness) / len(wetness)
    if max(wetness) >= 0.55 or average_wetness >= 0.48:
        return "Wet"
    if (
        max(wetness) >= 0.10
        or average_wetness >= 0.07
        or max(rain) >= 0.30
        or (rain[-1] >= 0.16 and rain[-1] > rain[0] + 0.08)
    ):
        return "Intermediate"
    return None


def recommended_starting_compound(
    track: Track,
    weather_payload: dict[str, Any],
    strategies: list[TireStrategy] | None,
    weather_scenario: dict[str, Any] | None = None,
) -> str | None:
    weather_override = weather_starting_compound(
        track,
        weather_payload,
        weather_scenario,
    )
    if weather_override is not None:
        return weather_override
    if strategies:
        return strategies[0].stints[0].compound
    return None


def _simulated_weather_starting_compound(
    track: Track,
    weather_scenario: dict[str, Any],
) -> str | None:
    climate = weather_scenario.get("climate") or climate_from_track(track)
    seed = int(weather_scenario["seed"])
    keyframes = build_race_keyframes(
        seed=seed,
        climate=climate,
        scenario=weather_scenario.get("scenario"),
    )
    initial = race_weather_at(keyframes, 0.0)
    wetness = float(initial["trackWetness"])
    lap_seconds = _base_lap_seconds(track)
    horizon_seconds = max(1.0, lap_seconds * 2.0)
    step_seconds = 5.0
    elapsed = 0.0
    peak_rain = float(initial["rainIntensity"])
    while elapsed < horizon_seconds:
        seconds = min(step_seconds, horizon_seconds - elapsed)
        progress = min(
            1.0,
            (elapsed + seconds) / max(lap_seconds * max(1, track.laps), 1.0),
        )
        frame = race_weather_at(keyframes, progress)
        peak_rain = max(peak_rain, float(frame["rainIntensity"]))
        wetness = update_track_wetness(
            wetness,
            float(frame["rainIntensity"]),
            seconds=seconds,
            track_temp_c=float(frame["trackTemp"]),
        )
        elapsed += seconds

    if wetness >= 0.52:
        return "Wet"
    if wetness >= 0.10 or peak_rain >= 0.30:
        return "Intermediate"
    return None


def _dynamic_programming_candidates(
    track: Track,
    lap_weather: list[dict[str, float | str]],
) -> list[TireStrategy]:
    stint_costs = _precompute_stint_costs(track, lap_weather)
    paths_by_state: dict[tuple[int, int, bool], list[_Path]] = {}

    for end_lap in range(1, track.laps + 1):
        for compound in TIRE_COMPOUNDS:
            stint = stint_costs.get((1, end_lap, compound))
            if stint is None:
                continue
            path = _Path(
                seconds=stint.seconds,
                stints=(stint,),
                slick_mask=_SLICK_BITS.get(compound, 0),
                used_wet_weather_tire=compound in WET_WEATHER_COMPOUNDS,
            )
            _add_path(
                paths_by_state,
                (end_lap, path.slick_mask, path.used_wet_weather_tire),
                path,
            )

    complete: list[_Path] = []
    pit_loss = pit_loss_seconds(track)
    for stint_count in range(1, 5):
        current_states = paths_by_state
        next_states: dict[tuple[int, int, bool], list[_Path]] = {}
        for (last_lap, _, _), paths in current_states.items():
            if last_lap == track.laps:
                complete.extend(paths)
            if last_lap >= track.laps or stint_count == 4:
                continue

            start_lap = last_lap + 1
            for end_lap in range(start_lap, track.laps + 1):
                for compound in TIRE_COMPOUNDS:
                    stint = stint_costs.get((start_lap, end_lap, compound))
                    if stint is None:
                        continue
                    for path in paths:
                        slick_mask = path.slick_mask | _SLICK_BITS.get(compound, 0)
                        used_wet = path.used_wet_weather_tire or compound in WET_WEATHER_COMPOUNDS
                        next_path = _Path(
                            seconds=path.seconds + pit_loss + stint.seconds,
                            stints=(*path.stints, stint),
                            slick_mask=slick_mask,
                            used_wet_weather_tire=used_wet,
                        )
                        _add_path(
                            next_states,
                            (end_lap, slick_mask, used_wet),
                            next_path,
                        )
        paths_by_state = next_states

    candidates = []
    for path in complete:
        if not 2 <= len(path.stints) <= 4:
            continue
        compounds = tuple(stint.compound for stint in path.stints)
        if not dry_tire_rule_satisfied(compounds):
            continue
        if _has_unjustified_short_weather_stint(path.stints, lap_weather):
            continue
        if _has_useless_short_slick_stint(
            path,
            track,
            stint_costs,
            pit_loss,
        ):
            continue
        stints = _build_strategy_stints(path.stints, lap_weather)
        estimated_time = path.seconds + _short_slick_stint_penalty(path.stints, track, pit_loss)
        candidates.append(
            TireStrategy(
                number=0,
                pit_stop_count=len(stints) - 1,
                stints=stints,
                estimated_time=round(estimated_time, 6),
            )
        )
    return candidates


def _short_slick_stint_penalty(
    stints: tuple[_StintCost, ...],
    track: Track,
    pit_loss: float,
) -> float:
    ideal_laps = _ideal_short_slick_stint_laps(track)
    penalty = 0.0
    for stint in stints:
        if stint.compound not in SLICK_COMPOUNDS:
            continue
        stint_laps = _stint_laps(stint)
        if stint_laps >= ideal_laps:
            continue
        shortfall = (ideal_laps - stint_laps) / ideal_laps
        penalty += pit_loss * shortfall**2
    return penalty


def _has_unjustified_short_weather_stint(
    stints: tuple[_StintCost, ...],
    lap_weather: list[dict[str, float | str]],
) -> bool:
    for stint in stints:
        if stint.compound not in WET_WEATHER_COMPOUNDS or _stint_laps(stint) > 1:
            continue
        weather = lap_weather[stint.start_lap - 1]
        if float(weather["wetness"]) < 0.12 and float(weather["rain"]) < 0.30:
            return True
    return False


def _has_useless_short_slick_stint(
    path: _Path,
    track: Track,
    stint_costs: dict[tuple[int, int, str], _StintCost],
    pit_loss: float,
) -> bool:
    ideal_laps = _ideal_short_slick_stint_laps(track)
    for index, stint in enumerate(path.stints):
        if stint.compound not in SLICK_COMPOUNDS or _stint_laps(stint) >= ideal_laps:
            continue
        alternative_seconds = _best_seconds_without_stint(path.stints, index, stint_costs, pit_loss)
        if alternative_seconds is None:
            continue
        benefit = alternative_seconds - path.seconds
        if benefit < pit_loss * USEFUL_SHORT_STINT_PIT_LOSS_FRACTION:
            return True
    return False


def _best_seconds_without_stint(
    stints: tuple[_StintCost, ...],
    index: int,
    stint_costs: dict[tuple[int, int, str], _StintCost],
    pit_loss: float,
) -> float | None:
    alternatives: list[tuple[_StintCost, ...]] = []

    if index > 0:
        previous = stints[index - 1]
        replacement = stint_costs.get(
            (previous.start_lap, stints[index].end_lap, previous.compound)
        )
        if replacement is not None:
            alternatives.append((*stints[: index - 1], replacement, *stints[index + 1 :]))

    if index + 1 < len(stints):
        following = stints[index + 1]
        replacement = stint_costs.get(
            (stints[index].start_lap, following.end_lap, following.compound)
        )
        if replacement is not None:
            alternatives.append((*stints[:index], replacement, *stints[index + 2 :]))

    valid_seconds = [
        _path_seconds(alternative, pit_loss)
        for alternative in alternatives
        if dry_tire_rule_satisfied(tuple(stint.compound for stint in alternative))
    ]
    return min(valid_seconds) if valid_seconds else None


def _path_seconds(stints: tuple[_StintCost, ...], pit_loss: float) -> float:
    return sum(stint.seconds for stint in stints) + pit_loss * max(0, len(stints) - 1)


def _ideal_short_slick_stint_laps(track: Track) -> int:
    return max(3, round(track.laps * SHORT_STINT_IDEAL_SHARE))


def _stint_laps(stint: _StintCost) -> int:
    return stint.end_lap - stint.start_lap + 1


def _add_path(
    states: dict[tuple[int, int, bool], list[_Path]],
    key: tuple[int, int, bool],
    path: _Path,
) -> None:
    values = states.setdefault(key, [])
    values.append(path)
    values.sort(key=lambda item: (item.seconds, _path_signature(item)))
    del values[DP_PATHS_PER_STATE:]


def _precompute_stint_costs(
    track: Track,
    lap_weather: list[dict[str, float | str]],
) -> dict[tuple[int, int, str], _StintCost]:
    result: dict[tuple[int, int, str], _StintCost] = {}
    corner_share = _high_speed_corner_share(track)
    base_lap_seconds = _base_lap_seconds(track)

    for start_lap in range(1, track.laps + 1):
        for compound in TIRE_COMPOUNDS:
            if not _compound_allowed_for_stint(compound, [lap_weather[start_lap - 1]]):
                continue
            condition = 100.0
            seconds = 0.0
            for end_lap in range(start_lap, track.laps + 1):
                weather = lap_weather[end_lap - 1]
                temperature = float(weather["temperature"])
                wetness = float(weather["wetness"])
                grip = tire_grip_multiplier(
                    compound,
                    condition,
                    track_temperature_c=temperature,
                    wetness=wetness,
                )
                seconds += base_lap_seconds / grip
                condition -= tire_wear_for_distance(
                    compound,
                    float(track.track_length_meters),
                    track_temperature_c=temperature,
                    wetness=wetness,
                    high_speed_corner_share=corner_share,
                )
                condition = max(0.0, condition)
                if condition < MIN_END_CONDITION:
                    break
                result[(start_lap, end_lap, compound)] = _StintCost(
                    compound=compound,
                    start_lap=start_lap,
                    end_lap=end_lap,
                    end_condition=condition,
                    seconds=seconds,
                )
    return result


def _compound_allowed_for_stint(
    compound: str,
    stint_weather: list[dict[str, float | str]],
) -> bool:
    if compound not in WET_WEATHER_COMPOUNDS:
        return True
    if compound == "Intermediate":
        wetness_threshold = INTERMEDIATE_MIN_WETNESS
        rain_threshold = INTERMEDIATE_MIN_RAIN
    else:
        wetness_threshold = WET_MIN_WETNESS
        rain_threshold = WET_MIN_RAIN
    if not stint_weather:
        return False
    first_lap = stint_weather[0]
    return (
        float(first_lap["wetness"]) >= wetness_threshold
        or float(first_lap["rain"]) >= rain_threshold
    )


def _weather_by_lap(
    laps: int,
    forecast: list[dict[str, Any]],
) -> list[dict[str, float | str]]:
    points = sorted(forecast, key=lambda item: float(item["progress"]))
    result: list[dict[str, float | str]] = []
    for lap in range(1, laps + 1):
        progress = 0.0 if laps <= 1 else (lap - 1) / (laps - 1)
        left = points[0]
        right = points[-1]
        for index in range(len(points) - 1):
            if float(points[index]["progress"]) <= progress <= float(points[index + 1]["progress"]):
                left, right = points[index], points[index + 1]
                break
        span = max(0.000001, float(right["progress"]) - float(left["progress"]))
        blend = max(0.0, min(1.0, (progress - float(left["progress"])) / span))
        result.append(
            {
                "wetness": (
                    _interpolate(left, right, "trackWetnessMin", blend)
                    + _interpolate(left, right, "trackWetnessMax", blend)
                )
                / 2,
                "temperature": _interpolate(left, right, "trackTemp", blend),
                "rain": _rain_level(left, right, blend),
                "confidence": str(left["confidence"] if blend < 0.5 else right["confidence"]),
            }
        )

    smoothed = []
    for index, item in enumerate(result):
        neighbors = result[max(0, index - 1) : min(len(result), index + 2)]
        smoothed.append(
            {
                **item,
                "wetness": sum(float(value["wetness"]) for value in neighbors) / len(neighbors),
                "rain": sum(float(value["rain"]) for value in neighbors) / len(neighbors),
            }
        )
    return smoothed


def _interpolate(
    left: dict[str, Any],
    right: dict[str, Any],
    key: str,
    blend: float,
) -> float:
    left_value = float(left.get(key, 0.0))
    return left_value + (float(right.get(key, left_value)) - left_value) * blend


def _rain_level(left: dict[str, Any], right: dict[str, Any], blend: float) -> float:
    levels = {"none": 0.0, "light": 0.16, "moderate": 0.45, "heavy": 0.8}
    left_value = levels.get(str(left.get("expectedRain", "none")), 0.0)
    right_value = levels.get(str(right.get("expectedRain", "none")), left_value)
    return left_value + (right_value - left_value) * blend


def _build_strategy_stints(
    path: tuple[_StintCost, ...],
    lap_weather: list[dict[str, float | str]],
) -> tuple[StrategyStint, ...]:
    result = []
    for index, stint in enumerate(path):
        if index == len(path) - 1:
            result.append(StrategyStint(stint.compound, stint.start_lap, stint.end_lap))
            continue
        confidence = str(lap_weather[stint.end_lap - 1]["confidence"])
        next_compound = path[index + 1].compound
        weather_change = (stint.compound in WET_WEATHER_COMPOUNDS) != (
            next_compound in WET_WEATHER_COMPOUNDS
        )
        radius = {"high": 1, "medium": 2, "low": 3}.get(confidence, 1)
        if not weather_change:
            radius = 1
        result.append(
            StrategyStint(
                compound=stint.compound,
                start_lap=stint.start_lap,
                end_lap=stint.end_lap,
                pit_window_start_lap=max(stint.start_lap, stint.end_lap - radius),
                pit_window_end_lap=min(path[index + 1].end_lap, stint.end_lap + radius),
            )
        )
    return tuple(result)


def strategy_stint_end_condition(
    track: Track,
    weather_payload: dict[str, Any],
    stint: StrategyStint,
) -> float:
    lap_weather = _weather_by_lap(track.laps, weather_payload["raceForecast"])
    cost = _precompute_stint_costs(track, lap_weather).get(
        (stint.start_lap, stint.end_lap, stint.compound)
    )
    return cost.end_condition if cost is not None else 0.0


def _high_speed_corner_share(track: Track) -> float:
    if not track.segments:
        return 0.3
    high_speed_length = sum(
        float(segment.length_meters)
        for segment in track.segments
        if segment.type.value == "high-speed-corner"
    )
    return high_speed_length / max(1.0, float(track.track_length_meters))


def _average_overtake_chance(track: Track) -> float:
    if not track.segments:
        return 0.25
    total_length = sum(float(segment.length_meters) for segment in track.segments)
    return sum(
        float(segment.overtake_chance) * float(segment.length_meters) for segment in track.segments
    ) / max(1.0, total_length)


def _base_lap_seconds(track: Track) -> float:
    segment_seconds = sum(
        float(segment.length_meters) / max(1.0, float(getattr(segment, "base_speed", 55.0)))
        for segment in track.segments
    )
    if segment_seconds > 0.0:
        return segment_seconds
    return float(track.track_length_meters) / 55.0


def _signature(strategy: TireStrategy) -> tuple[tuple[str, int, int], ...]:
    return tuple((stint.compound, stint.start_lap, stint.end_lap) for stint in strategy.stints)


def _fallback_strategies(
    track: Track,
    lap_weather: list[dict[str, float | str]],
    selected: list[TireStrategy],
) -> list[TireStrategy]:
    """Compatibility helper for diagnostics; production never publishes fallbacks."""
    existing = {_signature(strategy) for strategy in selected}
    return [
        candidate
        for candidate in sorted(
            _dynamic_programming_candidates(track, lap_weather),
            key=lambda item: (item.estimated_time, _signature(item)),
        )
        if _signature(candidate) not in existing
    ][: max(0, 3 - len(selected))]


def _path_signature(path: _Path) -> tuple[tuple[str, int, int], ...]:
    return tuple((stint.compound, stint.start_lap, stint.end_lap) for stint in path.stints)
