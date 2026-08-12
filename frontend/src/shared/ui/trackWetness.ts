export type TrackWetnessBand = "dry" | "damp" | "intermediate" | "wet";

export type TrackWetnessStyle = {
  band: TrackWetnessBand;
  stroke: string;
  opacity: number;
};

function clampWetness(value: number | undefined) {
  return Number.isFinite(value) ? Math.max(0, Math.min(1, value ?? 0)) : 0;
}

export function mapTrackWetness(trackWetness: number | undefined): TrackWetnessStyle {
  const wetness = clampWetness(trackWetness);
  if (wetness < 0.05) {
    return { band: "dry", stroke: "hsl(197 92% 64%)", opacity: 0 };
  }
  if (wetness < 0.12) {
    return { band: "damp", stroke: "hsl(210 34% 42%)", opacity: 0.22 };
  }
  if (wetness < 0.55) {
    return { band: "intermediate", stroke: "hsl(197 92% 64%)", opacity: 0.48 };
  }
  return { band: "wet", stroke: "hsl(199 95% 72%)", opacity: 0.78 };
}
