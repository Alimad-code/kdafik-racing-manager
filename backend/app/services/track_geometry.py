from __future__ import annotations

import math
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from app.domain.enums import TrackSegmentType

PathCommand = Literal["M", "L", "C", "Z"]

SVG_TOKEN_RE = re.compile(r"[MLCZmlcz]|[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")

TARGET_AVERAGE_TRACK_LENGTH_METERS = 2200.0
SVG_LENGTH_VARIANCE_EXPONENT = 0.25
TARGET_RACE_SECONDS = 10 * 60
MIN_RACE_LAPS = 14
MAX_RACE_LAPS = 28

HIGH_SPEED_CORNER_THRESHOLD = 0.20
LOW_SPEED_CORNER_THRESHOLD = 0.50

MIN_CORNER_SPEED = 25.0
HIGH_SPEED_CORNER_SPEED = 65.0
MAX_STRAIGHT_SPEED = 105.0
MAX_ACCEL_MPS2 = 7.0
MAX_BRAKE_MPS2 = 38.0


@dataclass(frozen=True)
class TrackGeometrySample:
    progress: float
    target_speed: float
    segment_type: TrackSegmentType
    severity: float


@dataclass(frozen=True)
class TrackGeometrySegment:
    segment_index: int
    type: TrackSegmentType
    length_meters: float
    base_speed: float
    overtake_chance: float


@dataclass(frozen=True)
class TrackGeometryMetrics:
    raw_svg_length: float
    track_length_meters: float
    predicted_lap_seconds: float
    laps: int


class TrackGeometryError(RuntimeError):
    pass


class TrackGeometryProfile:
    def __init__(self, samples: list[TrackGeometrySample]) -> None:
        if len(samples) < 2:
            raise TrackGeometryError("Track geometry profile requires at least two samples.")
        self.samples = sorted(samples, key=lambda sample: sample.progress)

    def target_speed(self, progress: float) -> float:
        return self._interpolate(progress, "target_speed")

    def segment_type(self, progress: float) -> TrackSegmentType:
        severity = self._interpolate(progress, "severity")
        if severity >= LOW_SPEED_CORNER_THRESHOLD:
            return TrackSegmentType.LOW_SPEED_CORNER
        if severity >= HIGH_SPEED_CORNER_THRESHOLD:
            return TrackSegmentType.HIGH_SPEED_CORNER
        return TrackSegmentType.STRAIGHT

    def _interpolate(self, progress: float, field: Literal["target_speed", "severity"]) -> float:
        normalized = progress % 1.0
        previous = self.samples[-1]
        previous_progress = previous.progress - 1.0

        for sample in self.samples:
            sample_progress = sample.progress
            if normalized <= sample_progress:
                span = sample_progress - previous_progress
                if span <= 0:
                    return float(getattr(sample, field))
                ratio = (normalized - previous_progress) / span
                return (
                    float(getattr(previous, field))
                    + (float(getattr(sample, field)) - float(getattr(previous, field))) * ratio
                )
            previous = sample
            previous_progress = sample_progress

        first = self.samples[0]
        sample_progress = first.progress + 1.0
        span = sample_progress - previous_progress
        ratio = (normalized - previous_progress) / span if span > 0 else 0.0
        return (
            float(getattr(previous, field))
            + (float(getattr(first, field)) - float(getattr(previous, field))) * ratio
        )


def build_track_geometry_profile(
    svg_path: str,
    *,
    track_length_meters: float,
    sample_count: int = 240,
) -> TrackGeometryProfile:
    points = _sample_svg_path(svg_path)
    resampled = _resample_evenly(points, sample_count)
    severities = _corner_severities(resampled)
    smoothed = _smooth_circular(severities, radius=5)
    target_speeds = _speed_profile(smoothed, track_length_meters)

    samples = [
        TrackGeometrySample(
            progress=index / sample_count,
            target_speed=target_speeds[index],
            segment_type=_segment_type(smoothed[index]),
            severity=smoothed[index],
        )
        for index in range(sample_count)
    ]
    return TrackGeometryProfile(samples)


def raw_svg_path_length(svg_path: str) -> float:
    """Return the sampled geometric length of a closed SVG circuit path."""
    points = _sample_svg_path(svg_path)
    return sum(
        _distance(previous, current) for previous, current in zip(points, points[1:], strict=False)
    )


def normalized_track_length_meters(
    raw_svg_length: float,
    average_raw_svg_length: float,
) -> float:
    if raw_svg_length <= 0 or average_raw_svg_length <= 0:
        raise TrackGeometryError("SVG lengths must be positive for normalization.")
    relative_length = raw_svg_length / average_raw_svg_length
    return TARGET_AVERAGE_TRACK_LENGTH_METERS * relative_length**SVG_LENGTH_VARIANCE_EXPONENT


def predicted_lap_seconds(profile: TrackGeometryProfile, track_length_meters: float) -> float:
    if track_length_meters <= 0:
        raise TrackGeometryError("Track length must be positive for lap prediction.")
    step_distance = track_length_meters / len(profile.samples)
    return sum(step_distance / max(sample.target_speed, 1.0) for sample in profile.samples)


def derived_laps_for_race(predicted_lap_seconds: float) -> int:
    if predicted_lap_seconds <= 0:
        raise TrackGeometryError("Predicted lap time must be positive.")
    return max(
        MIN_RACE_LAPS,
        min(MAX_RACE_LAPS, round(TARGET_RACE_SECONDS / predicted_lap_seconds)),
    )


def derived_track_geometry(
    svg_path: str,
    *,
    average_raw_svg_length: float,
    sample_count: int = 240,
) -> TrackGeometryMetrics:
    raw_length = raw_svg_path_length(svg_path)
    track_length = normalized_track_length_meters(raw_length, average_raw_svg_length)
    profile = build_track_geometry_profile(
        svg_path,
        track_length_meters=track_length,
        sample_count=sample_count,
    )
    lap_seconds = predicted_lap_seconds(profile, track_length)
    return TrackGeometryMetrics(
        raw_svg_length=raw_length,
        track_length_meters=track_length,
        predicted_lap_seconds=lap_seconds,
        laps=derived_laps_for_race(lap_seconds),
    )


def average_raw_svg_length(svg_paths: Iterable[str]) -> float:
    lengths = [raw_svg_path_length(path) for path in svg_paths]
    if not lengths:
        raise TrackGeometryError(
            "At least one SVG path is required to calculate an average length."
        )
    return sum(lengths) / len(lengths)


def build_track_geometry_segments(
    svg_path: str,
    *,
    track_length_meters: float,
    segment_count: int = 32,
    sample_count: int = 256,
) -> list[TrackGeometrySegment]:
    if segment_count < 4:
        raise TrackGeometryError("Track geometry requires at least four generated segments.")

    profile = build_track_geometry_profile(
        svg_path,
        track_length_meters=track_length_meters,
        sample_count=sample_count,
    )
    samples = profile.samples
    samples_per_segment = len(samples) / segment_count
    base_length = track_length_meters / segment_count

    segments: list[TrackGeometrySegment] = []
    assigned_length = 0.0
    for index in range(segment_count):
        start = int(round(index * samples_per_segment))
        end = int(round((index + 1) * samples_per_segment))
        bucket = samples[start:end] or [samples[index % len(samples)]]
        avg_speed = sum(sample.target_speed for sample in bucket) / len(bucket)
        avg_severity = sum(sample.severity for sample in bucket) / len(bucket)
        segment_type = _segment_type(avg_severity)

        if index == segment_count - 1:
            length_meters = track_length_meters - assigned_length
        else:
            length_meters = round(base_length, 1)
            assigned_length += length_meters

        previous_bucket = samples[
            int(round((index - 1) * samples_per_segment)) : int(round(index * samples_per_segment))
        ]
        previous_severity = (
            sum(sample.severity for sample in previous_bucket) / len(previous_bucket)
            if previous_bucket
            else avg_severity
        )

        segments.append(
            TrackGeometrySegment(
                segment_index=index + 1,
                type=segment_type,
                length_meters=round(length_meters, 1),
                base_speed=round(avg_speed, 1),
                overtake_chance=_overtake_chance(
                    segment_type,
                    avg_speed,
                    avg_severity,
                    previous_severity,
                ),
            )
        )

    return segments


def sample_track_points(svg_path: str, *, sample_count: int = 32) -> list[tuple[float, float]]:
    """Return equally spaced points along a supported circuit SVG path."""
    if sample_count < 2:
        raise TrackGeometryError("Track geometry requires at least two samples.")
    return _resample_evenly(_sample_svg_path(svg_path), sample_count)


def _sample_svg_path(svg_path: str) -> list[tuple[float, float]]:
    tokens = SVG_TOKEN_RE.findall(svg_path.replace(",", " "))
    if not tokens:
        raise TrackGeometryError("SVG path is empty.")

    points: list[tuple[float, float]] = []
    index = 0
    command: PathCommand | None = None
    current = (0.0, 0.0)
    subpath_start: tuple[float, float] | None = None

    def read_number() -> float:
        nonlocal index
        if index >= len(tokens) or tokens[index].isalpha():
            raise TrackGeometryError("Expected SVG path number.")
        value = float(tokens[index])
        index += 1
        return value

    while index < len(tokens):
        token = tokens[index]
        if token.isalpha():
            index += 1
            if token != token.upper():
                raise TrackGeometryError("Only absolute SVG path commands are supported.")
            if token not in {"M", "L", "C", "Z"}:
                raise TrackGeometryError(f"Unsupported SVG path command: {token}")
            command = token  # type: ignore[assignment]

        if command is None:
            raise TrackGeometryError("SVG path must start with a command.")

        if command == "M":
            current = (read_number(), read_number())
            subpath_start = current
            points.append(current)
            command = "L"
        elif command == "L":
            current = (read_number(), read_number())
            points.append(current)
        elif command == "C":
            control_1 = (read_number(), read_number())
            control_2 = (read_number(), read_number())
            end = (read_number(), read_number())
            points.extend(_sample_cubic(current, control_1, control_2, end))
            current = end
        elif command == "Z":
            if subpath_start is not None and _distance(current, subpath_start) > 0:
                points.append(subpath_start)
                current = subpath_start
            command = None

    if len(points) < 2:
        raise TrackGeometryError("SVG path produced fewer than two points.")
    return points


def _sample_cubic(
    start: tuple[float, float],
    control_1: tuple[float, float],
    control_2: tuple[float, float],
    end: tuple[float, float],
) -> list[tuple[float, float]]:
    chord = _distance(start, end)
    control_net = (
        _distance(start, control_1) + _distance(control_1, control_2) + _distance(control_2, end)
    )
    steps = max(12, min(80, int(control_net / max(chord, 1.0) * 18)))
    sampled = []
    for step in range(1, steps + 1):
        t = step / steps
        mt = 1.0 - t
        x = (
            mt**3 * start[0]
            + 3 * mt**2 * t * control_1[0]
            + 3 * mt * t**2 * control_2[0]
            + t**3 * end[0]
        )
        y = (
            mt**3 * start[1]
            + 3 * mt**2 * t * control_1[1]
            + 3 * mt * t**2 * control_2[1]
            + t**3 * end[1]
        )
        sampled.append((x, y))
    return sampled


def _resample_evenly(
    points: list[tuple[float, float]],
    sample_count: int,
) -> list[tuple[float, float]]:
    lengths = [0.0]
    for previous, current in zip(points, points[1:], strict=False):
        lengths.append(lengths[-1] + _distance(previous, current))
    total_length = lengths[-1]
    if total_length <= 0:
        raise TrackGeometryError("SVG path has zero length.")

    resampled = []
    source_index = 1
    for sample_index in range(sample_count):
        target_length = total_length * sample_index / sample_count
        while source_index < len(lengths) - 1 and lengths[source_index] < target_length:
            source_index += 1
        previous_length = lengths[source_index - 1]
        next_length = lengths[source_index]
        span = next_length - previous_length
        ratio = (target_length - previous_length) / span if span > 0 else 0.0
        previous_point = points[source_index - 1]
        next_point = points[source_index]
        resampled.append(
            (
                previous_point[0] + (next_point[0] - previous_point[0]) * ratio,
                previous_point[1] + (next_point[1] - previous_point[1]) * ratio,
            )
        )
    return resampled


def _corner_severities(points: list[tuple[float, float]]) -> list[float]:
    count = len(points)
    window = max(3, count // 80)
    severities = []
    for index in range(count):
        previous = points[(index - window) % count]
        current = points[index]
        following = points[(index + window) % count]
        incoming = (current[0] - previous[0], current[1] - previous[1])
        outgoing = (following[0] - current[0], following[1] - current[1])
        angle = _angle_between(incoming, outgoing)
        severities.append(min(1.0, (angle / 0.95) ** 0.8))
    return severities


def _speed_profile(severities: list[float], track_length_meters: float) -> list[float]:
    def lerp(start: float, end: float, progress: float) -> float:
        return start + (end - start) * progress

    local_targets = []
    for severity in severities:
        if severity < HIGH_SPEED_CORNER_THRESHOLD:
            target_speed = MAX_STRAIGHT_SPEED
        elif severity < LOW_SPEED_CORNER_THRESHOLD:
            progress = (severity - HIGH_SPEED_CORNER_THRESHOLD) / (
                LOW_SPEED_CORNER_THRESHOLD - HIGH_SPEED_CORNER_THRESHOLD
            )
            target_speed = lerp(MAX_STRAIGHT_SPEED, HIGH_SPEED_CORNER_SPEED, progress)
        else:
            progress = (severity - LOW_SPEED_CORNER_THRESHOLD) / (1.0 - LOW_SPEED_CORNER_THRESHOLD)
            target_speed = lerp(HIGH_SPEED_CORNER_SPEED, MIN_CORNER_SPEED, progress)
        local_targets.append(target_speed)
    local_targets = [
        max(MIN_CORNER_SPEED, min(MAX_STRAIGHT_SPEED, speed)) for speed in local_targets
    ]

    count = len(local_targets)
    step_distance = track_length_meters / count
    targets = local_targets[:]

    # Backward pass adds braking anticipation before slow corners.
    for offset in range(count * 2):
        index = (count - 1 - offset) % count
        next_index = (index + 1) % count
        brake_limited = math.sqrt(targets[next_index] ** 2 + 2 * MAX_BRAKE_MPS2 * step_distance)
        targets[index] = min(targets[index], brake_limited)

    return targets


def _smooth_circular(values: list[float], *, radius: int) -> list[float]:
    if radius <= 0:
        return values
    count = len(values)
    smoothed = []
    for index in range(count):
        total = 0.0
        weight_total = 0.0
        for offset in range(-radius, radius + 1):
            weight = radius + 1 - abs(offset)
            total += values[(index + offset) % count] * weight
            weight_total += weight
        smoothed.append(total / weight_total)
    return smoothed


def _segment_type(severity: float) -> TrackSegmentType:
    if severity >= LOW_SPEED_CORNER_THRESHOLD:
        return TrackSegmentType.LOW_SPEED_CORNER
    if severity >= HIGH_SPEED_CORNER_THRESHOLD:
        return TrackSegmentType.HIGH_SPEED_CORNER
    return TrackSegmentType.STRAIGHT


def _overtake_chance(
    segment_type: TrackSegmentType,
    avg_speed: float,
    avg_severity: float,
    previous_severity: float,
) -> float:
    if segment_type == TrackSegmentType.STRAIGHT:
        chance = 0.24 + max(0.0, avg_speed - 70.0) * 0.006
        if previous_severity >= 0.48:
            chance += 0.12
    elif segment_type == TrackSegmentType.HIGH_SPEED_CORNER:
        chance = 0.12 + max(0.0, avg_speed - 58.0) * 0.003
    else:
        chance = 0.04 + max(0.0, 0.45 - avg_severity) * 0.08
    return round(max(0.03, min(0.46, chance)), 3)


def _angle_between(a: tuple[float, float], b: tuple[float, float]) -> float:
    a_len = math.hypot(a[0], a[1])
    b_len = math.hypot(b[0], b[1])
    if a_len == 0 or b_len == 0:
        return 0.0
    dot = a[0] * b[0] + a[1] * b[1]
    value = max(-1.0, min(1.0, dot / (a_len * b_len)))
    return abs(math.acos(value))


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])
