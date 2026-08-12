import { useRef, useEffect, useState, useMemo, type RefObject } from "react";
import type { CarPosition } from "../model/useLiveRace";
import {
  advanceLateralMotion,
  requestLateralMotion,
  type LateralMotion
} from "../model/duelMotion";
import { useTrackViewport } from "@/shared/lib/useTrackViewport";
import { WetnessLayer } from "@/shared/ui/WetnessLayer";
import { getDriver } from "@/features/season/lib/seasonViewData";

interface LiveRaceMapProps {
  svgPath: string;
  cars: CarPosition[];
  playerDriverIds?: string[];
  speedMultiplier?: number;
  trackWetness?: number;
}

type RenderCarPosition = CarPosition & {
  lateral_offset: number;
};

const LANE_OFFSET_SCALE = 2;
const MAX_LATERAL_OFFSET = 10;
const PLAYER_LABEL_OFFSET = { x: 0, y: -32 };
const PLAYER_LABEL_SAFE_TOP = 56;

function useSvgScreenScale(svgRef: RefObject<SVGSVGElement | null>, dependency: unknown) {
  const [screenScale, setScreenScale] = useState(1);
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const update = () => {
      const matrix = svg.getScreenCTM();
      setScreenScale(matrix ? Math.hypot(matrix.a, matrix.b) || 1 : 1);
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(svg);
    return () => observer.disconnect();
  }, [svgRef, dependency]);
  return screenScale;
}

function clampOffset(value: number) {
  return Math.max(-MAX_LATERAL_OFFSET, Math.min(MAX_LATERAL_OFFSET, value));
}

function carLateralOffset(car: CarPosition) {
  if (typeof car.lane_offset_meters === "number") {
    return clampOffset(car.lane_offset_meters * LANE_OFFSET_SCALE);
  }

  if (typeof car.grid_lane === "number" && (car.distance_meters ?? 0) < 0) {
    return car.grid_lane === 0 ? -MAX_LATERAL_OFFSET : MAX_LATERAL_OFFSET;
  }

  return car.is_attacking ? MAX_LATERAL_OFFSET : 0;
}

function shouldRenderCar(car: CarPosition) {
  const status = car.status?.toUpperCase();
  return status !== "DNF" && status !== "RETIRED" && status !== "OUT";
}

function getRenderCars(cars: CarPosition[]): RenderCarPosition[] {
  return cars.filter(shouldRenderCar).map((car) => ({
    ...car,
    lateral_offset: carLateralOffset(car)
  }));
}

function playerDriverCode(car: RenderCarPosition) {
  const driver = getDriver(car.driver_id);
  if (driver.code && driver.code !== "---") return driver.code.toUpperCase();

  return (car.code ?? car.pilot_name ?? car.driver_id).slice(0, 3).toUpperCase();
}

function CarMarker({
  car,
  pathElement,
  totalLength,
  isPlayer,
  screenScale,
  speedMultiplier = 1
}: {
  car: RenderCarPosition;
  pathElement: SVGPathElement | null;
  totalLength: number;
  isPlayer: boolean;
  screenScale: number;
  speedMultiplier?: number;
}) {
  const [displayProgress, setDisplayProgress] = useState(car.lap_percentage);
  const targetProgressRef = useRef(car.lap_percentage);
  const startProgressRef = useRef(car.lap_percentage);
  const currentProgressRef = useRef(car.lap_percentage);
  const lastTickTimeRef = useRef<number | null>(null);
  const [displayLateralOffset, setDisplayLateralOffset] = useState(car.lateral_offset);
  const lateralCurrentRef = useRef(car.lateral_offset);
  const lateralMotionRef = useRef<LateralMotion | null>(null);

  useEffect(() => {
    // New target position from backend
    const newTarget = car.lap_percentage;

    // Snap logic: if tab was in background for a long time, just jump to target
    const currentPos = currentProgressRef.current;
    let diff = newTarget - currentPos;

    // Normalize diff for lap crossing
    if (diff < -0.5) diff += 1;
    if (diff > 0.5) diff -= 1;

    // If more than 10% track distance away, snap instead of sliding
    if (Math.abs(diff) > 0.1) {
      setDisplayProgress(newTarget);
      currentProgressRef.current = newTarget;
      startProgressRef.current = newTarget;
      targetProgressRef.current = newTarget;
      lastTickTimeRef.current = null; // Reset animation
    } else {
      startProgressRef.current = currentPos;
      targetProgressRef.current = newTarget;
      lastTickTimeRef.current = performance.now();
    }
  }, [car.lap_percentage]);

  useEffect(() => {
    const nextOffset = car.lateral_offset;
    if (Math.abs(nextOffset - lateralCurrentRef.current) > MAX_LATERAL_OFFSET * 1.8) {
      setDisplayLateralOffset(nextOffset);
      lateralCurrentRef.current = nextOffset;
      lateralMotionRef.current = null;
      return;
    }
    lateralMotionRef.current = requestLateralMotion(
      lateralMotionRef.current,
      lateralCurrentRef.current,
      nextOffset,
      performance.now()
    );
  }, [car.lateral_offset]);

  useEffect(() => {
    let requestRef: number;

    const animate = (time: DOMHighResTimeStamp) => {
      if (lastTickTimeRef.current !== null) {
        const elapsed = time - lastTickTimeRef.current;

        // Duration between ticks is 1000ms / multiplier
        const duration = 1000 / speedMultiplier;
        const t = Math.min(elapsed / duration, 1.0);

        const start = startProgressRef.current;
        const target = targetProgressRef.current;

        let diff = target - start;
        if (diff < -0.5) diff += 1;
        if (diff > 0.5) diff -= 1;

        let next = start + diff * t;

        // Wrap around for display
        if (next > 1) next -= 1;
        if (next < 0) next += 1;

        setDisplayProgress(next);
        currentProgressRef.current = next;
      }

      if (lateralMotionRef.current) {
        const motion = advanceLateralMotion(lateralMotionRef.current, time);
        setDisplayLateralOffset(motion.value);
        lateralCurrentRef.current = motion.value;
        lateralMotionRef.current = motion.next;
      }

      requestRef = requestAnimationFrame(animate);
    };

    requestRef = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(requestRef);
  }, [speedMultiplier]);

  const point = useMemo(() => {
    if (!pathElement || totalLength === 0) return { x: 0, y: 0 };
    const length = totalLength * displayProgress;
    const base = pathElement.getPointAtLength(length);
    const before = pathElement.getPointAtLength(Math.max(0, length - 1));
    const after = pathElement.getPointAtLength(Math.min(totalLength, length + 1));
    const dx = after.x - before.x;
    const dy = after.y - before.y;
    const normalLength = Math.hypot(dx, dy) || 1;
    return {
      x: base.x + (-dy / normalLength) * displayLateralOffset,
      y: base.y + (dx / normalLength) * displayLateralOffset
    };
  }, [pathElement, totalLength, displayLateralOffset, displayProgress]);

  return (
    <g>
      <circle
        cx={point.x}
        cy={point.y}
        r={isPlayer ? "11" : "8"}
        data-duel-id={car.duel_id ?? undefined}
        data-duel-phase={car.duel_phase ?? "NONE"}
        data-duel-role={car.duel_role ?? undefined}
        fill={car.team_color}
        stroke={isPlayer ? "#f8fafc" : car.is_attacking ? "#facc15" : "#fff"}
        strokeWidth={isPlayer ? "4" : car.is_attacking ? "4" : "2"}
        className="drop-shadow-sm transition-[stroke-width]"
      />
      {isPlayer ? (
        <g transform={`translate(${point.x} ${point.y})`}>
          <g
            data-testid={`player-car-label-${car.driver_id}`}
            data-label-offset-x={PLAYER_LABEL_OFFSET.x}
            data-label-offset-y={PLAYER_LABEL_OFFSET.y}
            transform={`scale(${1 / Math.max(screenScale, 0.001)}) translate(${PLAYER_LABEL_OFFSET.x} ${PLAYER_LABEL_OFFSET.y})`}
          >
            <rect
              x="-22"
              y="-12"
              width="44"
              height="24"
              fill="#111827"
              stroke={car.team_color || "#64748b"}
              strokeWidth="1.5"
            />
            <text
              textAnchor="middle"
              dominantBaseline="central"
              fill="#f8fafc"
              fontSize="14"
              fontFamily="JetBrains Mono, monospace"
              fontWeight="800"
            >
              {playerDriverCode(car)}
            </text>
          </g>
        </g>
      ) : null}
    </g>
  );
}

function StartFinishLine({
  pathElement,
  totalLength
}: {
  pathElement: SVGPathElement | null;
  totalLength: number;
}) {
  const line = useMemo(() => {
    if (!pathElement || totalLength === 0) return null;

    const start = pathElement.getPointAtLength(0);
    const after = pathElement.getPointAtLength(Math.min(totalLength, 12));
    const dx = after.x - start.x;
    const dy = after.y - start.y;
    const normalLength = Math.hypot(dx, dy) || 1;
    const nx = -dy / normalLength;
    const ny = dx / normalLength;
    const half = 28;

    return {
      x1: start.x - nx * half,
      y1: start.y - ny * half,
      x2: start.x + nx * half,
      y2: start.y + ny * half
    };
  }, [pathElement, totalLength]);

  if (!line) return null;

  return (
    <line
      data-testid="start-finish-line"
      x1={line.x1}
      y1={line.y1}
      x2={line.x2}
      y2={line.y2}
      stroke="#f8fafc"
      strokeWidth="6"
      strokeLinecap="square"
    />
  );
}

export function LiveRaceMap({
  svgPath,
  cars,
  playerDriverIds = [],
  speedMultiplier = 1,
  trackWetness
}: LiveRaceMapProps) {
  const pathRef = useRef<SVGPathElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [totalLength, setTotalLength] = useState<number>(0);
  const viewBox = useTrackViewport(pathRef, svgPath);
  const screenScale = useSvgScreenScale(svgRef, viewBox);

  useEffect(() => {
    try {
      if (pathRef.current) {
        setTotalLength(pathRef.current.getTotalLength());
      } else {
        setTotalLength(0);
      }
    } catch {
      setTotalLength(0);
    }
  }, [svgPath]);

  const renderCars = useMemo(() => getRenderCars(cars), [cars]);
  const orderedCars = useMemo(
    () => [
      ...renderCars.filter((car) => !playerDriverIds.includes(car.driver_id)),
      ...renderCars.filter((car) => playerDriverIds.includes(car.driver_id))
    ],
    [playerDriverIds, renderCars]
  );

  return (
    <div
      className="flex h-full w-full items-center justify-center px-2 pb-2"
      data-testid="live-track-map-frame"
      style={{ paddingTop: PLAYER_LABEL_SAFE_TOP }}
    >
      <svg
        ref={svgRef}
        className="h-full w-full overflow-visible drop-shadow-md"
        data-screen-scale={screenScale}
        data-testid="live-track-map"
        preserveAspectRatio="xMidYMid meet"
        viewBox={viewBox}
      >
        <path
          ref={pathRef}
          d={svgPath}
          fill="none"
          stroke="#334155"
          strokeWidth="34"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <WetnessLayer svgPath={svgPath} trackWetness={trackWetness} strokeWidth={24} />
        <path
          d={svgPath}
          fill="none"
          stroke="#64748b"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity="0.7"
        />
        {totalLength > 0 && (
          <StartFinishLine pathElement={pathRef.current} totalLength={totalLength} />
        )}
        {totalLength > 0 &&
          orderedCars.map((car) => (
            <CarMarker
              key={car.driver_id}
              car={car}
              pathElement={pathRef.current}
              totalLength={totalLength}
              isPlayer={playerDriverIds.includes(car.driver_id)}
              screenScale={screenScale}
              speedMultiplier={speedMultiplier}
            />
          ))}
      </svg>
    </div>
  );
}
