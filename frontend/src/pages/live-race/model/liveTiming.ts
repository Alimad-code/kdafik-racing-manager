import type { LeaderboardEntry, TimingCue } from "./useLiveRace";

export type ReceivedTimingCue = TimingCue & { receivedAt: number };
export interface TimingCueStore {
  active: ReceivedTimingCue[];
  recentIds: string[];
}
const RECENT_ID_LIMIT = 256;

export function formatLiveLapTime(ms?: number) {
  if (typeof ms !== "number") return "—";
  return `${Math.floor(ms / 60000)}:${((ms % 60000) / 1000).toFixed(3).padStart(6, "0")}`;
}
export function formatLiveGap(ms?: number | null) {
  return typeof ms === "number" ? `+${(ms / 1000).toFixed(3)}` : "—";
}
export function mergeTimingCueStore(
  store: TimingCueStore,
  incoming: TimingCue[],
  now: number
): TimingCueStore {
  const active = store.active.filter((cue) => now - cue.receivedAt < cue.durationMs);
  const ids = new Set(store.recentIds);
  const accepted: TimingCue[] = [];
  for (const cue of incoming) {
    if (ids.has(cue.id)) continue;
    ids.add(cue.id);
    accepted.push(cue);
  }
  return {
    active: [...active, ...accepted.map((cue) => ({ ...cue, receivedAt: now }))],
    recentIds: [...store.recentIds, ...accepted.map((cue) => cue.id)].slice(-RECENT_ID_LIMIT)
  };
}
export function timingLabel(
  entry: LeaderboardEntry,
  _cues: ReceivedTimingCue[],
  _now: number,
  _currentLap: number
) {
  void _cues;
  void _now;
  void _currentLap;

  if (entry.status === "IN_PITS") return "в питах";
  if (["DNF", "RETIRED", "OUT"].includes(entry.status)) return "выбыл";
  if (entry.status === "FINISHED") return "Финиш";
  if (entry.position === 1) return "Лидер";
  return formatLiveGap(entry.gapToAheadMs);
}
