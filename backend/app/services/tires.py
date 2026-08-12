from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TireCompound:
    name: str
    base_grip: float
    life_km: float
    ideal_temp_min: float
    ideal_temp_max: float


TIRE_COMPOUNDS = {
    "Soft": TireCompound("Soft", 1.03, 18.0, 25.0, 35.0),
    "Medium": TireCompound("Medium", 1.015, 27.0, 30.0, 40.0),
    "Hard": TireCompound("Hard", 1.00, 38.0, 35.0, 50.0),
    "Intermediate": TireCompound("Intermediate", 0.98, 28.0, 20.0, 30.0),
    "Wet": TireCompound("Wet", 0.95, 35.0, 15.0, 25.0),
}

SLICK_COMPOUNDS = frozenset({"Soft", "Medium", "Hard"})
WET_WEATHER_COMPOUNDS = frozenset({"Intermediate", "Wet"})
TIRE_CLIFF_CONDITION = 30.0
MIN_TIRE_MULTIPLIER = 0.2


def tire_wear_for_distance(
    compound_name: str,
    distance_meters: float,
    *,
    track_temperature_c: float,
    wetness: float = 0.0,
    high_speed_corner_share: float = 0.0,
) -> float:
    """Return condition loss from distance, temperature, cornering and surface."""
    compound = TIRE_COMPOUNDS.get(compound_name, TIRE_COMPOUNDS["Medium"])
    wear_to_cliff = 100.0 - TIRE_CLIFF_CONDITION
    distance_km = max(0.0, distance_meters) / 1000.0
    overheat = max(0.0, track_temperature_c - compound.ideal_temp_max)
    temperature_modifier = 1.0 + overheat * 0.04
    corner_modifier = 1.0 + 0.25 * max(0.0, min(1.0, high_speed_corner_share))
    bounded_wetness = max(0.0, min(1.0, wetness))
    surface_mismatch_modifier = 1.0
    if compound.name == "Intermediate" and bounded_wetness < 0.08:
        surface_mismatch_modifier = 1.55
    elif compound.name == "Wet":
        if bounded_wetness < 0.15:
            surface_mismatch_modifier = 1.9
        elif bounded_wetness < 0.45:
            surface_mismatch_modifier = 1.7
    return (
        distance_km
        / compound.life_km
        * wear_to_cliff
        * temperature_modifier
        * corner_modifier
        * surface_mismatch_modifier
    )


def tire_grip_multiplier(
    compound_name: str,
    condition: float,
    *,
    track_temperature_c: float,
    wetness: float,
) -> float:
    """Calculate remaining grip, including wear, temperature and surface mismatch."""
    compound = TIRE_COMPOUNDS.get(compound_name, TIRE_COMPOUNDS["Medium"])
    bounded_condition = max(0.0, min(100.0, condition))
    bounded_wetness = max(0.0, min(1.0, wetness))

    if bounded_condition > TIRE_CLIFF_CONDITION:
        grip = compound.base_grip - (100.0 - bounded_condition) * 0.0005
    else:
        cliff_severity = (TIRE_CLIFF_CONDITION - bounded_condition) * 0.005
        grip = compound.base_grip - 0.035 - cliff_severity

    if track_temperature_c < compound.ideal_temp_min:
        grip -= (compound.ideal_temp_min - track_temperature_c) * 0.0025
    elif track_temperature_c > compound.ideal_temp_max:
        grip -= (track_temperature_c - compound.ideal_temp_max) * 0.0015

    if compound.name in SLICK_COMPOUNDS:
        if bounded_wetness > 0.05:
            grip -= bounded_wetness * 2.5
    elif compound.name == "Intermediate":
        if bounded_wetness < 0.10:
            grip -= 0.12
        elif bounded_wetness > 0.50:
            grip -= (bounded_wetness - 0.50) * 1.0
    elif compound.name == "Wet" and bounded_wetness < 0.50:
        grip -= 0.22

    return max(MIN_TIRE_MULTIPLIER, grip)


def dry_tire_rule_required(compounds: list[str] | tuple[str, ...]) -> bool:
    return not bool(set(compounds) & WET_WEATHER_COMPOUNDS)


def dry_tire_rule_satisfied(compounds: list[str] | tuple[str, ...]) -> bool:
    if not dry_tire_rule_required(compounds):
        return True
    return len(set(compounds) & SLICK_COMPOUNDS) >= 2
