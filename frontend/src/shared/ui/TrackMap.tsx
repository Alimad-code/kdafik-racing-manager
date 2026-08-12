import { useRef } from "react";
import { useTrackViewport } from "@/shared/lib/useTrackViewport";
import { cn } from "@/shared/lib/utils";
import { WetnessLayer } from "@/shared/ui/WetnessLayer";

type TrackMapVariant = "mini" | "panel" | "square";

type TrackMapProps = {
  svgPath?: string;
  label?: string;
  variant?: TrackMapVariant;
  className?: string;
  "aria-label"?: string;
  trackWetness?: number;
};

const variantClassName: Record<TrackMapVariant, string> = {
  mini: "h-24 md:h-full md:min-h-24",
  panel: "h-44",
  square: "aspect-square h-full w-full"
};

export function TrackMap({
  svgPath,
  label,
  variant = "mini",
  className,
  trackWetness,
  "aria-label": ariaLabel
}: TrackMapProps) {
  const pathData = svgPath?.trim();
  const pathRef = useRef<SVGPathElement>(null);
  const viewBox = useTrackViewport(pathRef, pathData);

  return (
    <div
      aria-label={ariaLabel ?? label ?? "Track map"}
      className={cn(
        "relative flex min-w-0 overflow-hidden border border-line bg-surface-track shadow-insetLine",
        variantClassName[variant],
        className
      )}
      role="img"
    >
      <div
        className="absolute inset-0 opacity-35"
        style={{
          backgroundImage:
            "linear-gradient(hsl(var(--line) / 0.5) 1px, transparent 1px), linear-gradient(90deg, hsl(var(--line) / 0.5) 1px, transparent 1px)",
          backgroundSize: "18px 18px"
        }}
      />

      {pathData ? (
        <svg
          aria-hidden="true"
          className={cn(
            "relative z-10 h-full w-full drop-shadow-md",
            variant === "square" ? "p-2" : "p-2.5"
          )}
          preserveAspectRatio="xMidYMid meet"
          viewBox={viewBox}
        >
          <path
            ref={pathRef}
            d={pathData}
            fill="none"
            stroke="hsl(var(--muted-foreground))"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={variant === "panel" ? 22 : 28}
          />
          <path
            d={pathData}
            fill="none"
            stroke="hsl(var(--primary))"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={variant === "panel" ? 8 : 10}
          />
          <WetnessLayer
            svgPath={pathData}
            trackWetness={trackWetness}
            strokeWidth={variant === "panel" ? 9 : 11}
          />
        </svg>
      ) : (
        <div className="relative z-10 flex h-full w-full flex-col items-center justify-center gap-2 px-3 text-center">
          <span className="h-px w-12 bg-primary/70" />
          <span className="font-mono text-[10px] font-black uppercase tracking-[0.18em] text-muted-foreground">
            TRACK MAP PENDING
          </span>
          {label ? (
            <span className="max-w-full truncate font-mono text-[9px] font-black uppercase tracking-[0.16em] text-primary/80">
              {label}
            </span>
          ) : null}
        </div>
      )}

      {pathData && label ? (
        <span className="absolute bottom-1.5 left-2 z-20 max-w-[calc(100%-1rem)] truncate font-mono text-[9px] font-black uppercase tracking-[0.14em] text-muted-foreground">
          {label}
        </span>
      ) : null}
    </div>
  );
}
