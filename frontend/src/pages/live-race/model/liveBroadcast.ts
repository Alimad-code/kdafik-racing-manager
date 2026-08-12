import type { BroadcastEvent } from "./useLiveRace";
import { resolveLiveDriverName } from "./liveDriverName";

export const BROADCAST_DURATION_MS = 4000;

export interface ActiveBroadcast {
  event: BroadcastEvent;
  startedAtMs: number;
}

export interface BroadcastQueueState {
  active: ActiveBroadcast | null;
  pending: BroadcastEvent[];
}

export function createBroadcastQueue(): BroadcastQueueState {
  return { active: null, pending: [] };
}

export function enqueueBroadcastEvents(
  state: BroadcastQueueState,
  incoming: BroadcastEvent[],
  nowMs: number,
  seenIds: Set<string>
): BroadcastQueueState {
  const known = new Set([
    ...seenIds,
    ...state.pending.map((event) => event.id),
    ...(state.active ? [state.active.event.id] : [])
  ]);
  const accepted = incoming.filter((event) => {
    if (known.has(event.id)) return false;
    known.add(event.id);
    seenIds.add(event.id);
    return true;
  });
  if (!state.active && accepted.length) {
    return {
      ...state,
      active: { event: accepted[0], startedAtMs: nowMs },
      pending: [...state.pending, ...accepted.slice(1)]
    };
  }
  return { ...state, pending: [...state.pending, ...accepted] };
}

export function advanceBroadcastQueue(
  state: BroadcastQueueState,
  nowMs: number
): BroadcastQueueState {
  let active = state.active;
  const pending = [...state.pending];
  while (active && nowMs - active.startedAtMs >= BROADCAST_DURATION_MS) {
    const next = pending.shift();
    active = next ? { event: next, startedAtMs: active.startedAtMs + BROADCAST_DURATION_MS } : null;
  }
  return { active, pending };
}

export function formatBroadcastLapTime(milliseconds: number) {
  const safe = Math.max(0, Math.round(milliseconds));
  const minutes = Math.floor(safe / 60000);
  const seconds = Math.floor((safe % 60000) / 1000);
  const millis = safe % 1000;
  return `${minutes}:${String(seconds).padStart(2, "0")}.${String(millis).padStart(3, "0")}`;
}

export function resolveBroadcastPilotName(event: BroadcastEvent) {
  const fallbackName = event.pilotName.trim() || event.pilotCode;
  return resolveLiveDriverName(event.driverId, fallbackName).toUpperCase();
}
