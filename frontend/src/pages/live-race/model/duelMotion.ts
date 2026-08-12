export function duelLateralAnimationMs(phase?: string | null) {
  return phase === "RETURN" ? 800 : 700;
}

export interface LateralMotion {
  from: number;
  target: number;
  startedAtMs: number;
  durationMs: number;
  queuedReturn: boolean;
}

export function requestLateralMotion(
  active: LateralMotion | null,
  current: number,
  target: number,
  nowMs: number
): LateralMotion | null {
  if (active?.target === target) return active;

  const isStillMovingAside =
    active !== null &&
    active.target !== 0 &&
    target === 0 &&
    nowMs - active.startedAtMs < active.durationMs;
  if (isStillMovingAside) {
    return { ...active, queuedReturn: true };
  }

  if (current === target) return null;
  return {
    from: current,
    target,
    startedAtMs: nowMs,
    durationMs: target === 0 ? duelLateralAnimationMs("RETURN") : duelLateralAnimationMs(),
    queuedReturn: false
  };
}

export function advanceLateralMotion(active: LateralMotion, nowMs: number) {
  const progress = Math.min(1, Math.max(0, (nowMs - active.startedAtMs) / active.durationMs));
  const eased = 1 - (1 - progress) * (1 - progress);
  const value = active.from + (active.target - active.from) * eased;

  if (progress < 1) return { value, next: active };
  if (!active.queuedReturn) return { value: active.target, next: null };
  return {
    value: active.target,
    next: {
      from: active.target,
      target: 0,
      startedAtMs: nowMs,
      durationMs: duelLateralAnimationMs("RETURN"),
      queuedReturn: false
    } satisfies LateralMotion
  };
}
