import type { CSSProperties } from "react";
import { TeamIcon } from "@/shared/ui/TeamIcon";
import { cn } from "@/shared/lib/utils";
import { formatBroadcastLapTime, resolveBroadcastPilotName } from "../model/liveBroadcast";
import type { BroadcastEvent } from "../model/useLiveRace";

export function LiveBroadcastOverlay({ event }: { event: BroadcastEvent | null }) {
  if (!event) return null;
  const isFastest = event.type === "FASTEST_LAP";
  const isFinalLap = event.type === "FINAL_LAP_STARTED";
  const pilotName = resolveBroadcastPilotName(event);
  return (
    <div
      aria-live="polite"
      className="pointer-events-none absolute left-1/2 top-14 z-50 w-max max-w-[calc(100%-2rem)] -translate-x-1/2"
      role="status"
    >
      <div
        data-broadcast-type={event.type}
        data-testid="live-broadcast-overlay"
        className={cn(
          "flex max-w-full flex-wrap items-center border bg-secondary/95 font-mono uppercase shadow-2xl backdrop-blur",
          isFastest || isFinalLap ? "border-violet-400" : "border-[color:var(--broadcast-accent)]"
        )}
        style={
          !isFastest && !isFinalLap
            ? ({ "--broadcast-accent": event.teamColor } as CSSProperties)
            : undefined
        }
      >
        <span
          className={cn(
            "shrink-0 px-3 py-2 text-[11px] font-black",
            isFastest || isFinalLap
              ? "bg-violet-600 text-white"
              : "text-[color:var(--broadcast-accent)]"
          )}
        >
          {isFastest ? "БЫСТРЕЙШИЙ КРУГ" : isFinalLap ? "ПОСЛЕДНИЙ КРУГ" : "НОВЫЙ ЛИДЕР"}
        </span>
        <TeamIcon
          aria-hidden="true"
          className="ml-3 size-5 shrink-0"
          color={event.teamColor}
          teamId={event.teamId}
        />
        <span
          className={cn(
            "min-w-0 break-words px-3 py-1 text-base font-black leading-tight sm:text-xl",
            isFastest || isFinalLap ? "text-violet-300" : "text-foreground"
          )}
        >
          {pilotName}
        </span>
        {isFinalLap ? (
          <span className="hidden px-3 text-xs font-bold normal-case text-foreground sm:inline">
            Лидер начал финальный круг
          </span>
        ) : null}
        {isFastest && event.lapTimeMs !== null ? (
          <span className="ml-auto shrink-0 px-3 text-xl font-black text-foreground">
            {formatBroadcastLapTime(event.lapTimeMs)}
          </span>
        ) : null}
      </div>
    </div>
  );
}
