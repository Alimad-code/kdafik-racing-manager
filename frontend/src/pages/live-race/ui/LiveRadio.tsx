import { type CSSProperties } from "react";
import { getReadableTeamAccent } from "@/shared/lib/teamAccent";
import { cn } from "@/shared/lib/utils";
import { TeamIcon } from "@/shared/ui/TeamIcon";
import { resolveLiveDriverName } from "../model/liveDriverName";
import type { RadioMessage } from "../model/useLiveRace";

interface LiveRadioProps {
  message: RadioMessage | null;
}

const FALLBACK_TEAM_COLOR = "#64748b";

export function LiveRadio({ message }: LiveRadioProps) {
  if (!message) return null;

  const accent = getReadableTeamAccent(message.teamColor || FALLBACK_TEAM_COLOR);
  const isTeamMessage = message.source === "team";

  return (
    <div className="pointer-events-none absolute right-5 top-1/2 z-40 flex -translate-y-1/2 flex-col items-end">
      <div
        key={message.id}
        data-testid="live-radio-overlay"
        className="w-max min-w-[220px] max-w-[320px] border border-line bg-secondary shadow-xl"
        style={{ "--team-accent": accent } as CSSProperties}
      >
        <div
          className="border-b px-2.5 py-2 text-right"
          style={{ borderColor: "var(--team-accent)" }}
        >
          <p
            className="break-words font-mono text-base font-black uppercase leading-tight"
            style={{ color: "var(--team-accent)" }}
          >
            {resolveLiveDriverName(message.driverId, message.pilotName)}
          </p>
          <div className="mt-1.5 flex items-center justify-end gap-2">
            <TeamIcon className="size-4" color={accent} teamId={message.teamId} />
            <span className="font-mono text-base font-black uppercase leading-none tracking-[0.04em] text-foreground">
              Радио
            </span>
          </div>
        </div>
        <p
          className={cn(
            "px-2.5 py-2.5 font-mono text-sm font-black uppercase leading-tight",
            isTeamMessage ? "text-left text-foreground" : "text-right"
          )}
          style={isTeamMessage ? undefined : { color: "var(--team-accent)" }}
        >
          "{message.text}"
        </p>
      </div>
    </div>
  );
}
