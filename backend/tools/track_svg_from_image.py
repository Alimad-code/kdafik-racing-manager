from __future__ import annotations

import argparse
import base64
import html
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
from numpy.typing import NDArray

CloseMode = Literal["auto", "yes", "no"]


class TrackSvgError(RuntimeError):
    pass


@dataclass(frozen=True)
class GeneratedTrackSvg:
    path: str
    mask: NDArray[np.uint8]
    skeleton: NDArray[np.uint8]
    points: NDArray[np.float32]
    subpaths: list[NDArray[np.float32]]
    source_size: tuple[int, int]
    close_path: bool


def require_cv2():
    try:
        import cv2  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        raise TrackSvgError(
            "OpenCV is required for image tracing. Install dev dependencies with "
            "`python -m pip install -e .[dev]` or install `opencv-contrib-python`."
        ) from exc

    if not hasattr(cv2, "ximgproc") or not hasattr(cv2.ximgproc, "thinning"):
        raise TrackSvgError(
            "`cv2.ximgproc.thinning` is unavailable. Install `opencv-contrib-python`, "
            "not the base `opencv-python` package."
        )
    return cv2


def threshold_track(
    image: NDArray[np.uint8],
    threshold: int,
    *,
    blur: int = 0,
) -> NDArray[np.uint8]:
    if image.ndim != 2:
        raise TrackSvgError("Expected a grayscale image.")
    if not 0 <= threshold <= 255:
        raise TrackSvgError("--threshold must be between 0 and 255.")
    if blur < 0 or blur % 2 == 0 and blur != 0:
        raise TrackSvgError("--blur must be 0 or a positive odd integer.")

    cv2 = require_cv2()
    source = cv2.GaussianBlur(image, (blur, blur), 0) if blur else image
    mask = np.where(source < threshold, 255, 0).astype(np.uint8)
    if int(np.count_nonzero(mask)) == 0:
        raise TrackSvgError("No dark track pixels found. Try increasing --threshold.")
    return mask


def clean_mask(mask: NDArray[np.uint8], *, morph_kernel: int = 3) -> NDArray[np.uint8]:
    cv2 = require_cv2()
    if morph_kernel <= 0 or morph_kernel % 2 == 0:
        raise TrackSvgError("--morph-kernel must be a positive odd integer.")

    kernel = np.ones((morph_kernel, morph_kernel), np.uint8)
    opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)
    return keep_largest_component(closed)


def keep_largest_component(mask: NDArray[np.uint8]) -> NDArray[np.uint8]:
    cv2 = require_cv2()
    component_count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    if component_count <= 1:
        raise TrackSvgError("No connected track component found.")

    component_ids = range(1, component_count)
    largest_id = max(component_ids, key=lambda idx: int(stats[idx, cv2.CC_STAT_AREA]))
    largest = np.where(labels == largest_id, 255, 0).astype(np.uint8)
    if int(np.count_nonzero(largest)) == 0:
        raise TrackSvgError("Largest track component is empty.")
    return largest


def skeletonize(mask: NDArray[np.uint8]) -> NDArray[np.uint8]:
    cv2 = require_cv2()
    skeleton = cv2.ximgproc.thinning(mask)
    if int(np.count_nonzero(skeleton)) == 0:
        raise TrackSvgError("Skeleton is empty after thinning.")
    return skeleton


def neighbor_points(point: tuple[int, int], pixels: set[tuple[int, int]]) -> list[tuple[int, int]]:
    x, y = point
    result: list[tuple[int, int]] = []
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            candidate = (x + dx, y + dy)
            if candidate in pixels:
                result.append(candidate)
    return result


def trace_skeleton(skeleton: NDArray[np.uint8]) -> NDArray[np.float32]:
    ys, xs = np.where(skeleton > 0)
    pixels = set(zip(xs.tolist(), ys.tolist(), strict=True))
    if not pixels:
        raise TrackSvgError("No skeleton pixels found.")

    endpoints = [point for point in pixels if len(neighbor_points(point, pixels)) == 1]
    start = min(endpoints or pixels, key=lambda point: (point[1], point[0]))
    if endpoints:
        traced = trace_open_skeleton(start, pixels)
        if len(traced) >= int(len(pixels) * 0.85):
            return np.array(traced, dtype=np.float32)
    else:
        traced = trace_loop_skeleton(start, pixels)
        if len(traced) >= int(len(pixels) * 0.7):
            return np.array(traced, dtype=np.float32)

    return np.array(trace_all_skeleton_edges(start, pixels), dtype=np.float32)


def trace_skeleton_subpaths(skeleton: NDArray[np.uint8]) -> list[NDArray[np.float32]]:
    return [trace_skeleton(skeleton)]


def trace_open_skeleton(
    start: tuple[int, int],
    pixels: set[tuple[int, int]],
) -> list[tuple[int, int]]:
    path = [start]
    visited = {start}
    previous: tuple[int, int] | None = None
    current = start

    while True:
        options = [point for point in neighbor_points(current, pixels) if point not in visited]
        if not options:
            break

        next_point = choose_next_point(previous, current, options)
        visited.add(next_point)
        path.append(next_point)
        previous, current = current, next_point

    if len(path) < 2:
        raise TrackSvgError("Skeleton trace produced fewer than two points.")
    return path


def trace_loop_skeleton(
    start: tuple[int, int],
    pixels: set[tuple[int, int]],
) -> list[tuple[int, int]]:
    path = [start]
    visited = {start}
    previous: tuple[int, int] | None = None
    current = start

    while True:
        neighbors = neighbor_points(current, pixels)
        options = [point for point in neighbors if point not in visited]
        if not options:
            break

        next_point = choose_next_point(previous, current, options)
        visited.add(next_point)
        path.append(next_point)
        previous, current = current, next_point

        if len(path) > 12 and distance_squared(current, start) <= 2:
            break

    if len(path) < 2:
        raise TrackSvgError("Skeleton trace produced fewer than two points.")
    return path


def trace_all_skeleton_edges(
    start: tuple[int, int],
    pixels: set[tuple[int, int]],
) -> list[tuple[int, int]]:
    adjacency = {point: set(neighbor_points(point, pixels)) for point in pixels}
    odd_points = [point for point, neighbors in adjacency.items() if len(neighbors) % 2 == 1]
    if odd_points:
        start = min(odd_points, key=lambda point: (point[1], point[0]))

    stack = [start]
    circuit: list[tuple[int, int]] = []

    while stack:
        current = stack[-1]
        if adjacency[current]:
            previous = stack[-2] if len(stack) >= 2 else None
            options = list(adjacency[current])
            next_point = choose_next_point(previous, current, options)
            adjacency[current].remove(next_point)
            adjacency[next_point].remove(current)
            stack.append(next_point)
        else:
            circuit.append(stack.pop())

    path = list(reversed(circuit))

    if len(path) < 2:
        raise TrackSvgError("Skeleton trace produced fewer than two points.")
    return path


def choose_next_point(
    previous: tuple[int, int] | None,
    current: tuple[int, int],
    options: list[tuple[int, int]],
) -> tuple[int, int]:
    if previous is None:
        return min(options, key=lambda point: distance_squared(current, point))

    direction = (current[0] - previous[0], current[1] - previous[1])

    def score(point: tuple[int, int]) -> tuple[float, int]:
        candidate = (point[0] - current[0], point[1] - current[1])
        dot = direction[0] * candidate[0] + direction[1] * candidate[1]
        return (-dot, distance_squared(current, point))

    return min(options, key=score)


def distance_squared(a: tuple[int, int], b: tuple[int, int]) -> int:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


def simplify_points(points: NDArray[np.float32], tolerance: float) -> NDArray[np.float32]:
    if tolerance <= 0:
        return points

    keep = rdp_keep_mask(points, tolerance)
    simplified = points[keep]
    if len(simplified) < 2:
        return points
    return trim_long_closing_tail(simplified.astype(np.float32))


def smooth_points(
    points: NDArray[np.float32],
    *,
    iterations: int,
    closed: bool,
) -> NDArray[np.float32]:
    if iterations <= 0:
        return points
    if len(points) < 3:
        return points

    smoothed = points
    for _ in range(iterations):
        source = smoothed
        pairs: list[NDArray[np.float32]] = []
        if not closed:
            pairs.append(source[0:1])

        segment_count = len(source) if closed else len(source) - 1
        for index in range(segment_count):
            current = source[index]
            following = source[(index + 1) % len(source)]
            pairs.append((current * 0.75 + following * 0.25)[None, :])
            pairs.append((current * 0.25 + following * 0.75)[None, :])

        if not closed:
            pairs.append(source[-1:])
        smoothed = np.concatenate(pairs).astype(np.float32)

    return smoothed


def trim_long_closing_tail(points: NDArray[np.float32]) -> NDArray[np.float32]:
    if len(points) < 4:
        return points

    segments = np.linalg.norm(points[1:] - points[:-1], axis=1)
    median_segment = float(np.median(segments))
    last_segment = float(segments[-1])
    previous_to_start = float(np.linalg.norm(points[-2] - points[0]))
    if (
        median_segment > 0
        and last_segment > max(80.0, median_segment * 8)
        and previous_to_start <= max(20.0, median_segment * 3)
    ):
        return points[:-1]
    return points


def rdp_keep_mask(points: NDArray[np.float32], tolerance: float) -> NDArray[np.bool_]:
    keep = np.zeros(len(points), dtype=np.bool_)
    keep[0] = True
    keep[-1] = True

    stack = [(0, len(points) - 1)]
    while stack:
        start, end = stack.pop()
        if end <= start + 1:
            continue

        segment_start = points[start]
        segment_end = points[end]
        candidates = points[start + 1 : end]
        distances = point_line_distances(candidates, segment_start, segment_end)
        max_index = int(np.argmax(distances))
        if float(distances[max_index]) > tolerance:
            split = start + 1 + max_index
            keep[split] = True
            stack.append((start, split))
            stack.append((split, end))

    return keep


def normalize_subpaths(
    subpaths: list[NDArray[np.float32]],
    *,
    size: int,
    padding: int,
) -> list[NDArray[np.float32]]:
    if not subpaths:
        raise TrackSvgError("At least one subpath is required.")
    all_points = np.concatenate(subpaths)
    normalized_all = normalize_points(all_points, size=size, padding=padding)

    normalized: list[NDArray[np.float32]] = []
    start = 0
    for subpath in subpaths:
        end = start + len(subpath)
        normalized.append(normalized_all[start:end])
        start = end
    return normalized


def point_line_distances(
    points: NDArray[np.float32],
    start: NDArray[np.float32],
    end: NDArray[np.float32],
) -> NDArray[np.float32]:
    line = end - start
    norm = float(np.linalg.norm(line))
    if norm == 0:
        return np.linalg.norm(points - start, axis=1)
    shifted = points - start
    cross = line[0] * shifted[:, 1] - line[1] * shifted[:, 0]
    return np.abs(cross) / norm


def normalize_points(
    points: NDArray[np.float32],
    *,
    size: int,
    padding: int,
) -> NDArray[np.float32]:
    if size <= 0:
        raise TrackSvgError("--size must be positive.")
    if padding < 0 or padding * 2 >= size:
        raise TrackSvgError("--padding must be non-negative and smaller than half --size.")

    min_xy = points.min(axis=0)
    max_xy = points.max(axis=0)
    span = max_xy - min_xy
    longest = float(max(span[0], span[1]))
    if longest == 0:
        raise TrackSvgError("Cannot normalize a zero-size point cloud.")

    scale = (size - padding * 2) / longest
    return ((points - min_xy) * scale + padding).astype(np.float32)


def should_close_path(points: NDArray[np.float32], mode: CloseMode, size: int) -> bool:
    if mode == "yes":
        return True
    if mode == "no":
        return False
    distance = float(np.linalg.norm(points[0] - points[-1]))
    return distance <= max(12.0, size * 0.035)


def svg_path_from_points(points: NDArray[np.float32], *, close_path: bool) -> str:
    if len(points) < 2:
        raise TrackSvgError("At least two points are required for an SVG path.")

    parts = [f"M {points[0][0]:.0f} {points[0][1]:.0f}"]
    parts.extend(f"L {x:.0f} {y:.0f}" for x, y in points[1:])
    if close_path:
        parts.append("Z")
    return " ".join(parts)


def svg_path_from_subpaths(subpaths: list[NDArray[np.float32]]) -> str:
    parts: list[str] = []
    for points in subpaths:
        if len(points) < 2:
            continue
        parts.append(f"M {points[0][0]:.0f} {points[0][1]:.0f}")
        parts.extend(f"L {x:.0f} {y:.0f}" for x, y in points[1:])
    if not parts:
        raise TrackSvgError("At least one non-empty subpath is required.")
    return " ".join(parts)


def generate_track_svg_path(
    image_path: Path,
    *,
    threshold: int,
    simplify: float,
    size: int,
    padding: int,
    close_mode: CloseMode,
    blur: int = 0,
    morph_kernel: int = 3,
    smooth: int = 0,
) -> GeneratedTrackSvg:
    cv2 = require_cv2()
    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise TrackSvgError(f"Could not read image: {image_path}")

    mask = threshold_track(image, threshold, blur=blur)
    mask = clean_mask(mask, morph_kernel=morph_kernel)
    skeleton = skeletonize(mask)
    raw_subpaths = trace_skeleton_subpaths(skeleton)
    if len(raw_subpaths) == 1:
        points = simplify_points(raw_subpaths[0], simplify)
        points = normalize_points(points, size=size, padding=padding)
        close_path = should_close_path(points, close_mode, size)
        points = smooth_points(points, iterations=smooth, closed=close_path)
        path = svg_path_from_points(points, close_path=close_path)
        subpaths = [points]
    else:
        simplified_subpaths = [
            simplify_points(subpath, simplify) for subpath in raw_subpaths if len(subpath) >= 2
        ]
        subpaths = normalize_subpaths(simplified_subpaths, size=size, padding=padding)
        points = np.concatenate(subpaths)
        close_path = False
        path = svg_path_from_subpaths(subpaths)
    return GeneratedTrackSvg(
        path=path,
        mask=mask,
        skeleton=skeleton,
        points=points,
        subpaths=subpaths,
        source_size=(int(image.shape[1]), int(image.shape[0])),
        close_path=close_path,
    )


def write_outputs(
    *,
    source_image: Path,
    generated: GeneratedTrackSvg,
    out_dir: Path,
    size: int,
) -> None:
    cv2 = require_cv2()
    out_dir.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_dir / "mask.png"), generated.mask)
    cv2.imwrite(str(out_dir / "skeleton.png"), generated.skeleton)
    write_preview_svg(
        source_image=source_image,
        path=generated.path,
        out_path=out_dir / "preview.svg",
        size=size,
    )
    render_preview_png(generated.path, out_dir / "preview.png", size)


def write_preview_svg(*, source_image: Path, path: str, out_path: Path, size: int) -> None:
    mime_type = "image/png" if source_image.suffix.lower() == ".png" else "image/jpeg"
    image_data = base64.b64encode(source_image.read_bytes()).decode("ascii")
    escaped_path = html.escape(path, quote=True)
    image_href = f"data:{mime_type};base64,{image_data}"
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}">
  <rect width="{size}" height="{size}" fill="white"/>
  <image
    href="{image_href}"
    x="0"
    y="0"
    width="{size}"
    height="{size}"
    opacity="0.28"
    preserveAspectRatio="xMidYMid meet"
  />
  <path
    d="{escaped_path}"
    fill="none"
    stroke="#e11d48"
    stroke-width="16"
    stroke-linecap="round"
    stroke-linejoin="round"
  />
</svg>
"""
    out_path.write_text(svg, encoding="utf-8")


def render_preview_png(path: str, png_path: Path, size: int) -> None:
    cv2 = require_cv2()
    preview = np.full((size, size, 3), 255, dtype=np.uint8)
    skeleton = np.zeros((size, size), dtype=np.uint8)
    draw_path_on_image(skeleton, path)
    preview[skeleton > 0] = (72, 29, 225)
    cv2.imwrite(str(png_path), preview)


def draw_path_on_image(image: NDArray[np.uint8], path: str) -> None:
    cv2 = require_cv2()
    tokens = path.split()
    points: list[tuple[int, int]] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in {"M", "L"}:
            x = int(round(float(tokens[index + 1])))
            y = int(round(float(tokens[index + 2])))
            points.append((x, y))
            index += 3
        elif token == "Z":
            index += 1
        else:
            raise TrackSvgError(f"Unexpected SVG path token in preview renderer: {token}")

    if len(points) >= 2:
        cv2.polylines(image, [np.array(points, dtype=np.int32)], False, 255, 8)
    if path.endswith(" Z") and len(points) >= 3:
        cv2.line(image, points[-1], points[0], 255, 8)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a backend svg_path from a black-on-white track map image."
    )
    parser.add_argument("image", type=Path, help="Input PNG/JPG track image.")
    parser.add_argument("--threshold", type=int, default=180)
    parser.add_argument("--simplify", type=float, default=3.0)
    parser.add_argument("--size", type=int, default=1000)
    parser.add_argument("--padding", type=int, default=40)
    parser.add_argument("--out-dir", type=Path, default=Path("generated/track-svg"))
    parser.add_argument("--close", choices=("auto", "yes", "no"), default="auto")
    parser.add_argument("--blur", type=int, default=0)
    parser.add_argument("--morph-kernel", type=int, default=3)
    parser.add_argument("--smooth", type=int, default=0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        generated = generate_track_svg_path(
            args.image,
            threshold=args.threshold,
            simplify=args.simplify,
            size=args.size,
            padding=args.padding,
            close_mode=args.close,
            blur=args.blur,
            morph_kernel=args.morph_kernel,
            smooth=args.smooth,
        )
        write_outputs(
            source_image=args.image,
            generated=generated,
            out_dir=args.out_dir,
            size=args.size,
        )
    except TrackSvgError as exc:
        print(f"Could not generate track SVG path: {exc}", file=sys.stderr)
        return 1

    print(generated.path)
    print(f"Preview written to: {args.out_dir / 'preview.svg'}", file=sys.stderr)
    print(f"Debug images written to: {args.out_dir}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
