from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from hashlib import sha256
from typing import Any
from uuid import UUID

RACE_KEYFRAME_COUNT = 9
RAIN_ACTIVE_THRESHOLD = 0.03
SCENARIO_TYPES = (
    "dry_race",
    "light_shower",
    "passing_rain",
    "wet_start",
    "late_rain",
    "full_wet_race",
)


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def stable_weather_seed(season_id: UUID | str, stage_id: UUID | str) -> int:
    raw = f"weather:{season_id}:{stage_id}".encode()
    return int.from_bytes(sha256(raw).digest()[:8], byteorder="big", signed=False)


def climate_from_track(track: Any) -> dict[str, float]:
    return {
        "rainChance": float(track.rain_probability),
        "weatherChange": float(track.variability),
        "trackTempMinC": float(track.track_temperature_min_c),
        "trackTempMaxC": float(track.track_temperature_max_c),
    }


def create_weather_scenario(*, seed: int, climate: Mapping[str, float]) -> dict[str, Any]:
    return {
        "seed": int(seed),
        "climate": _copy_climate(climate),
        "scenario": _build_weather_scenario(seed, climate),
    }


def _copy_climate(climate: Mapping[str, float]) -> dict[str, float]:
    return {
        "rainChance": float(climate["rainChance"]),
        "weatherChange": float(climate["weatherChange"]),
        "trackTempMinC": float(climate["trackTempMinC"]),
        "trackTempMaxC": float(climate["trackTempMaxC"]),
    }


def _derived_seed(seed: int, label: str) -> int:
    return int.from_bytes(sha256(f"{seed}:{label}".encode()).digest()[:8], "big")


def _build_weather_scenario(seed: int, climate: Mapping[str, float]) -> dict[str, Any]:
    rng = random.Random(_derived_seed(seed, "scenario"))
    rain_chance = clamp(float(climate["rainChance"]))
    weather_change = clamp(float(climate["weatherChange"]))
    weights = [
        (1.0 - rain_chance) * 1.4,
        rain_chance * (0.35 + weather_change * 0.45),
        rain_chance * (0.50 + weather_change * 0.35),
        rain_chance * 0.35,
        rain_chance * (0.25 + weather_change * 0.55),
        rain_chance**1.5 * (0.25 + (1.0 - weather_change) * 0.35),
    ]
    total = sum(weights)
    selected = "dry_race"
    if total > 0:
        cursor = rng.random() * total
        for scenario_type, weight in zip(SCENARIO_TYPES, weights, strict=True):
            cursor -= weight
            if cursor <= 0:
                selected = scenario_type
                break

    if selected == "dry_race":
        return {
            "type": selected,
            "start": None,
            "end": None,
            "peak": 0.0,
            "initialWetness": rng.uniform(0.0, 0.03),
        }
    if selected == "light_shower":
        start = rng.uniform(0.10, 0.55)
        return _rain_scenario(
            selected,
            start,
            min(1.0, start + rng.uniform(0.12, 0.22)),
            rng.uniform(0.18, 0.34),
            rng.uniform(0.0, 0.04),
        )
    if selected == "passing_rain":
        start = rng.uniform(0.15, 0.45)
        return _rain_scenario(
            selected,
            start,
            min(1.0, start + rng.uniform(0.25, 0.42)),
            rng.uniform(0.35, 0.65),
            rng.uniform(0.0, 0.06),
        )
    if selected == "wet_start":
        return _rain_scenario(
            selected, 0.0, rng.uniform(0.12, 0.32), rng.uniform(0.15, 0.45), rng.uniform(0.25, 0.55)
        )
    if selected == "late_rain":
        return _rain_scenario(
            selected, rng.uniform(0.58, 0.82), 1.0, rng.uniform(0.35, 0.70), rng.uniform(0.0, 0.04)
        )
    return _rain_scenario(
        selected,
        rng.uniform(0.0, 0.10),
        rng.uniform(0.75, 1.0),
        rng.uniform(0.45, 0.85),
        rng.uniform(0.30, 0.65),
    )


def _rain_scenario(
    scenario_type: str, start: float, end: float, peak: float, initial: float
) -> dict[str, Any]:
    return {
        "type": scenario_type,
        "start": clamp(start),
        "end": clamp(max(start + 1e-9, end)),
        "peak": clamp(peak),
        "initialWetness": clamp(initial),
    }


def smoothstep(x: float) -> float:
    x = clamp(x)
    return x * x * (3.0 - 2.0 * x)


def rain_intensity_at(
    progress: float, start: float | None, end: float | None, peak: float
) -> float:
    if start is None or end is None or progress < start or progress > end:
        return 0.0
    phase = (progress - start) / (end - start)
    if phase < 0.25:
        factor = smoothstep(phase / 0.25)
    elif phase > 0.75:
        factor = smoothstep((1.0 - phase) / 0.25)
    else:
        factor = 1.0
    return round(clamp(peak * factor), 6)


def update_track_wetness(
    track_wetness: float, rain_intensity: float, *, seconds: float, track_temp_c: float
) -> float:
    temp_factor = clamp((track_temp_c - 15.0) / 35.0)
    rain_gain = 0.0045 * rain_intensity * seconds
    drying = (0.00012 + 0.00075 * temp_factor) * seconds
    drying *= 1.0 - 0.45 * rain_intensity
    return round(clamp(track_wetness + rain_gain - drying), 6)


def precipitation_from_intensity(rain_intensity: float) -> str:
    if rain_intensity < 0.03:
        return "none"
    if rain_intensity < 0.30:
        return "light"
    if rain_intensity < 0.65:
        return "moderate"
    return "heavy"


def precipitation_from_rain(rain_intensity: float | Sequence[float]) -> str:
    if isinstance(rain_intensity, (int, float)):
        return precipitation_from_intensity(float(rain_intensity))
    values = [float(value) for value in rain_intensity]
    return precipitation_from_intensity(sum(values) / len(values) if values else 0.0)


def recommended_tire_for_wetness(track_wetness: float) -> str:
    if track_wetness >= 0.55:
        return "Wet"
    if track_wetness >= 0.12:
        return "Intermediate"
    return "Medium"


def build_race_keyframes(
    *,
    seed: int,
    climate: Mapping[str, float],
    scenario: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    scenario = dict(scenario or _build_weather_scenario(seed, climate))
    rng = random.Random(_derived_seed(seed, "race:weather"))
    minimum = float(climate["trackTempMinC"])
    maximum = float(climate["trackTempMaxC"])
    temperature = rng.uniform(minimum, maximum)
    target = rng.uniform(minimum, maximum)
    wetness = float(scenario["initialWetness"])
    frames = []
    for index in range(RACE_KEYFRAME_COUNT):
        progress = index / 8
        rain = rain_intensity_at(progress, scenario["start"], scenario["end"], scenario["peak"])
        if index > 0:
            wetness = update_track_wetness(wetness, rain, seconds=120.0, track_temp_c=temperature)
            temperature = clamp(temperature, minimum, maximum)
        frames.append(
            {
                "progress": round(progress, 3),
                "scenario": scenario["type"],
                "precipitation": precipitation_from_intensity(rain),
                "rainIntensity": round(rain, 4),
                "trackWetness": round(wetness, 4),
                "trackTemp": round(temperature, 1),
            }
        )
        temperature += (target - temperature) * 0.18 + rng.uniform(-0.8, 0.8) * clamp(
            float(climate["weatherChange"])
        )
        temperature = max(minimum, min(maximum, temperature))
    return frames


def race_weather_at(keyframes: Sequence[Mapping[str, Any]], progress: float) -> dict[str, Any]:
    bounded = clamp(progress)
    scaled = bounded * (len(keyframes) - 1)
    left_index = min(int(scaled), len(keyframes) - 1)
    right_index = min(left_index + 1, len(keyframes) - 1)
    blend = scaled - left_index
    left, right = keyframes[left_index], keyframes[right_index]
    rain = _interpolate(left, right, "rainIntensity", blend)
    return {
        "scenario": keyframes[0]["scenario"],
        "precipitation": precipitation_from_intensity(rain),
        "rainIntensity": round(rain, 6),
        "trackWetness": round(_interpolate(left, right, "trackWetness", blend), 6),
        "trackTemp": round(_interpolate(left, right, "trackTemp", blend), 6),
    }


def build_weather_payload(scenario: Mapping[str, Any]) -> dict[str, Any]:
    seed = int(scenario["seed"])
    climate = _copy_climate(scenario["climate"])
    keyframes = build_race_keyframes(
        seed=seed,
        climate=climate,
        scenario=scenario.get("scenario"),
    )
    practice = {name: _session_snapshot(seed, climate, name) for name in ("fp1", "fp2", "fp3")}
    return {
        "practice": practice,
        "qualifying": _session_snapshot(seed, climate, "qualifying"),
        "raceForecast": build_race_forecast(seed=seed, climate=climate, keyframes=keyframes),
    }


def _session_snapshot(seed: int, climate: Mapping[str, float], name: str) -> dict[str, Any]:
    rng = random.Random(_derived_seed(seed, f"session:{name}"))
    rainy = rng.random() < clamp(float(climate["rainChance"]))
    rain = rng.uniform(0.15, 0.75) if rainy else 0.0
    wetness = clamp(rain * rng.uniform(0.35, 0.80)) if rainy else rng.uniform(0.0, 0.04)
    temperature = rng.uniform(float(climate["trackTempMinC"]), float(climate["trackTempMaxC"]))
    return {
        "precipitation": precipitation_from_intensity(rain),
        "trackTemp": round(temperature, 1),
        "rainIntensity": round(rain, 4),
        "trackWetness": round(wetness, 4),
    }


def build_race_forecast(
    *, seed: int, climate: Mapping[str, float], keyframes: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    points = [
        ("start", 0.0, "high", 0.05, 0.03, 1.0),
        ("one-third", 1 / 3, "high", 0.10, 0.07, 2.0),
        ("two-thirds", 2 / 3, "medium", 0.18, 0.12, 3.0),
        ("finish", 1.0, "low", 0.28, 0.18, 4.0),
    ]
    result = []
    for point, progress, confidence, rain_error, wetness_error, temp_error in points:
        actual = race_weather_at(keyframes, progress)
        rng = random.Random(_derived_seed(seed, f"forecast:{point}"))
        rain_chance = clamp(
            float(climate["rainChance"]) * 0.35
            + actual["rainIntensity"] * 0.50
            + actual["trackWetness"] * 0.25
            + rng.uniform(-rain_error, rain_error)
        )
        forecast_wetness = clamp(
            actual["trackWetness"] + rng.uniform(-wetness_error, wetness_error)
        )
        result.append(
            {
                "point": point,
                "progress": round(progress, 3),
                "confidence": confidence,
                "rainChance": round(rain_chance, 3),
                "expectedRain": precipitation_from_intensity(
                    clamp(actual["rainIntensity"] + rng.uniform(-rain_error, rain_error))
                ),
                "trackWetnessMin": round(clamp(forecast_wetness - wetness_error), 4),
                "trackWetnessMax": round(clamp(forecast_wetness + wetness_error), 4),
                "trackTemp": round(float(actual["trackTemp"]), 1),
                "temperatureMinC": round(float(actual["trackTemp"]) - temp_error, 1),
                "temperatureMaxC": round(float(actual["trackTemp"]) + temp_error, 1),
            }
        )
    return result


def _interpolate(
    left: Mapping[str, Any], right: Mapping[str, Any], key: str, blend: float
) -> float:
    a = float(left[key])
    return a + (float(right[key]) - a) * blend
