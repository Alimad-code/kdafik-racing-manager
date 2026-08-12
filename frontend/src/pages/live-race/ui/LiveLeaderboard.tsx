import { useEffect, useState, type CSSProperties } from "react";
import { Timer } from "lucide-react";
import { getReadableTeamAccent } from "@/shared/lib/teamAccent";
import { cn } from "@/shared/lib/utils";
import { TeamIcon } from "@/shared/ui/TeamIcon";
import { resolveLiveDriverName } from "../model/liveDriverName";
import { timingLabel, type ReceivedTimingCue } from "../model/liveTiming";
import type { LeaderboardEntry, RaceStatus } from "../model/useLiveRace";
import { LiveTireIndicator } from "./LiveTireIndicator";

interface LiveLeaderboardProps {
  status: RaceStatus;
  entries: LeaderboardEntry[];
  timingCues?: ReceivedTimingCue[];
  playerDriverIds: string[];
}

const FALLBACK_TEAM_COLOR = "#64748b";

function isInPits(entry: LeaderboardEntry) {
  return entry.status === "IN_PITS";
}

function isRetired(entry: LeaderboardEntry) {
  return entry.status === "DNF" || entry.status === "RETIRED" || entry.status === "OUT";
}

function RaceStatusMarker({ entry }: { entry: LeaderboardEntry }) {
  if (entry.status === "FINISHED") {
    return (
      <span
        aria-label="Финишировал"
        data-status-marker="finished"
        role="img"
        title="Финишировал"
        className="grid size-3.5 grid-cols-2 overflow-hidden border border-foreground/80"
      >
        <span className="bg-foreground" />
        <span className="bg-background" />
        <span className="bg-background" />
        <span className="bg-foreground" />
      </span>
    );
  }

  if (entry.isFastestLap) {
    return (
      <span
        aria-label="Быстрейший круг"
        data-status-marker="fastest-lap"
        role="img"
        title="Быстрейший круг"
        className="flex size-3.5 items-center justify-center bg-violet-600 text-violet-50"
      >
        <Timer aria-hidden="true" className="size-3" strokeWidth={2.5} />
      </span>
    );
  }

  return null;
}

export function LiveLeaderboard({
  status,
  entries,
  timingCues = [],
  playerDriverIds
}: LiveLeaderboardProps) {
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    if (!timingCues.length) return;
    const timer = window.setInterval(() => setNow(Date.now()), 100);
    return () => window.clearInterval(timer);
  }, [timingCues.length]);

  return (
    <div
      data-testid="live-leaderboard-list"
      className="flex h-full min-h-0 flex-1 flex-col overflow-hidden bg-background/35 shadow-insetLine"
    >
      {entries.length ? (
        entries.map((entry) => {
          const accent = getReadableTeamAccent(entry.teamColor || FALLBACK_TEAM_COLOR);
          const driverName = resolveLiveDriverName(entry.driverId, entry.pilotName);
          const retired = isRetired(entry);
          const inPits = isInPits(entry);
          const isPlayerEntry = playerDriverIds.includes(entry.driverId);

          return (
            <div
              key={entry.id}
              data-testid={`live-leaderboard-row-${entry.id}`}
              className={cn(
                "grid min-h-0 flex-1 grid-cols-[24px_18px_minmax(110px,1fr)_66px_14px_18px] items-center border-b border-line/70 font-mono uppercase last:border-0",
                retired ? "bg-muted/30 opacity-60" : "bg-card/95",
                isPlayerEntry &&
                  "border-l-2 bg-primary/10 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.08)]"
              )}
              style={{ "--team-accent": accent } as CSSProperties}
            >
              <div
                className={cn(
                  "flex h-full min-h-0 items-center justify-center text-sm font-black leading-none text-foreground",
                  entry.position === 1 ? "bg-primary" : "bg-background"
                )}
              >
                {entry.position}
              </div>
              <div className="flex h-full min-h-0 items-center justify-center">
                <TeamIcon className="size-3.5" color={accent} teamId={entry.teamId} />
              </div>
              <div
                className="truncate px-0.5 text-[10px] font-black leading-none text-foreground"
                title={driverName}
              >
                {driverName}
              </div>
              <div
                className={cn(
                  "whitespace-nowrap px-0.5 text-right text-[10px] font-black leading-none tracking-tight",
                  inPits ? "text-[color:var(--team-accent)]" : "text-foreground",
                  retired && "text-muted-foreground"
                )}
              >
                {timingLabel(entry, timingCues, now, status.currentLap)}
              </div>
              <div className="flex items-center justify-center">
                {inPits || retired ? null : <LiveTireIndicator compound={entry.tireCompound} />}
              </div>
              <div
                data-testid={`live-status-${entry.id}`}
                className="flex h-full min-h-0 items-center justify-center"
              >
                <RaceStatusMarker entry={entry} />
              </div>
            </div>
          );
        })
      ) : (
        <div className="p-4 text-center font-mono text-sm font-bold uppercase text-muted-foreground">
          Ожидание данных
        </div>
      )}
    </div>
  );
}
