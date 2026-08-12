import { mapTrackWetness } from "./trackWetness";

type WetnessLayerProps = {
  svgPath: string;
  trackWetness?: number;
  strokeWidth: number;
};

export function WetnessLayer({ svgPath, trackWetness, strokeWidth }: WetnessLayerProps) {
  const style = mapTrackWetness(trackWetness);
  if (style.opacity === 0) return null;

  return (
    <path
      d={svgPath}
      className="transition-opacity duration-700 ease-linear"
      data-testid="track-wetness-layer"
      data-wetness-band={style.band}
      data-wetness={Math.max(0, Math.min(1, trackWetness ?? 0)).toFixed(3)}
      fill="none"
      stroke={style.stroke}
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={strokeWidth}
      opacity={style.opacity}
    />
  );
}
