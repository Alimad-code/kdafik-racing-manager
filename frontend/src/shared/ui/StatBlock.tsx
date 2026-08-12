import type { CSSProperties } from "react";
import { getReadableTeamAccent } from "@/shared/lib/teamAccent";
import { cn } from "@/shared/lib/utils";

type StatBlockDensity = "compact" | "normal" | "prominent";

type StatBlockProps = {
  label: string;
  value: string;
  detail?: string;
  density?: StatBlockDensity;
  status?: string;
  accent?: string;
};

const densityClassName: Record<StatBlockDensity, string> = {
  compact: "p-3",
  normal: "p-3 sm:p-4",
  prominent: "p-4 sm:p-5"
};

const valueClassName: Record<StatBlockDensity, string> = {
  compact: "text-xl",
  normal: "text-xl sm:text-2xl",
  prominent: "text-3xl sm:text-4xl"
};

export function StatBlock({
  label,
  value,
  detail,
  density = "normal",
  status,
  accent
}: StatBlockProps) {
  const readableAccent = accent ? getReadableTeamAccent(accent) : undefined;
  const style = readableAccent ? ({ "--team-accent": readableAccent } as CSSProperties) : undefined;

  return (
    <div
      className={cn("race-panel", densityClassName[density])}
      style={
        accent
          ? ({
              ...style,
              borderColor: "color-mix(in srgb, var(--team-accent) 85%, white 15%)",
              background: "color-mix(in srgb, var(--team-accent) 25%, transparent)"
            } as CSSProperties)
          : style
      }
    >
      <div className="flex items-start justify-between gap-3">
        <p className="metadata-label">{label}</p>
        {status ? (
          <span
            className={cn(
              "font-mono text-[10px] font-black",
              accent ? "text-[var(--team-accent)]" : "text-primary"
            )}
          >
            {status}
          </span>
        ) : null}
      </div>
      <p className={cn("mt-2 timing-value sm:mt-3", valueClassName[density])}>{value}</p>
      {detail ? <p className="mt-2 text-xs text-muted-foreground">{detail}</p> : null}
    </div>
  );
}
