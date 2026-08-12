export function pitPhaseLabel(phase?: string | null) {
  const labels: Record<string, string> = {
    ENTRY: "Въезд",
    SERVICE: "Пит-стоп",
    EXIT: "Выезд"
  };
  return labels[phase ?? ""] ?? "Пит-стоп";
}

export interface PitTimingInterpolationInput {
  serverSeconds: number | null | undefined;
  syncedAtMs: number;
  nowMs: number;
  gameTimeRate: number;
  active: boolean;
}

export function interpolatePitGameSeconds(input: PitTimingInterpolationInput) {
  const base = Math.max(0, input.serverSeconds ?? 0);
  if (!input.active) return base;
  const elapsedSeconds = Math.max(0, input.nowMs - input.syncedAtMs) / 1000;
  return base + elapsedSeconds * Math.max(0, input.gameTimeRate);
}

export function legacyPitElapsed(service?: number | null, waiting?: number | null) {
  return Math.max(0, service ?? 0) + Math.max(0, waiting ?? 0);
}

export function interpolatePitService(
  input: PitTimingInterpolationInput,
  duration: number | null | undefined,
  phase: string | null | undefined
) {
  const value = interpolatePitGameSeconds({
    ...input,
    active: input.active && phase === "SERVICE"
  });
  return typeof duration === "number" ? Math.min(value, Math.max(0, duration)) : value;
}
