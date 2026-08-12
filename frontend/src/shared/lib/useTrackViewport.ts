import { useLayoutEffect, useState, type RefObject } from "react";

export const FALLBACK_TRACK_VIEWBOX = "0 0 1000 1000";

const MINIMUM_TRACK_PADDING = 24;
const TRACK_PADDING_RATIO = 0.08;

type TrackBounds = Pick<DOMRect, "x" | "y" | "width" | "height">;

function isValidBounds({ x, y, width, height }: TrackBounds) {
  return [x, y, width, height].every(Number.isFinite) && width > 0 && height > 0;
}

export function getTrackViewBox(bounds: TrackBounds) {
  if (!isValidBounds(bounds)) {
    return FALLBACK_TRACK_VIEWBOX;
  }

  const padding = Math.max(
    Math.max(bounds.width, bounds.height) * TRACK_PADDING_RATIO,
    MINIMUM_TRACK_PADDING
  );
  const x = bounds.x - padding;
  const y = bounds.y - padding;
  const width = bounds.width + padding * 2;
  const height = bounds.height + padding * 2;

  return `${x} ${y} ${width} ${height}`;
}

/**
 * Keeps every rendering of a catalog track path framed by its actual SVG bounds.
 * The path reference may still be used by callers for live-race geometry methods.
 */
export function useTrackViewport(pathRef: RefObject<SVGPathElement | null>, svgPath?: string) {
  const [viewBox, setViewBox] = useState(FALLBACK_TRACK_VIEWBOX);

  useLayoutEffect(() => {
    const pathData = svgPath?.trim();
    const pathElement = pathRef.current;

    if (!pathData || !pathElement) {
      setViewBox(FALLBACK_TRACK_VIEWBOX);
      return;
    }

    try {
      setViewBox(getTrackViewBox(pathElement.getBBox()));
    } catch {
      setViewBox(FALLBACK_TRACK_VIEWBOX);
    }
  }, [pathRef, svgPath]);

  return viewBox;
}
