import type { CSSProperties, ReactNode } from "react";
import { getReadableTeamAccent } from "@/shared/lib/teamAccent";
import { cn } from "@/shared/lib/utils";

type MetricRowProps = {
  label: string;
  value: ReactNode;
  detail?: ReactNode;
  trend?: "up" | "down" | "flat";
  accent?: string;
};

const trendClassName = {
  up: "text-success",
  down: "text-danger",
  flat: "text-muted-foreground"
};

export function MetricRow({ label, value, detail, trend = "flat", accent }: MetricRowProps) {
  const readableAccent = accent ? getReadableTeamAccent(accent) : undefined;
  const style = readableAccent ? ({ "--team-accent": readableAccent } as CSSProperties) : undefined;

  return (
    <div
      className={cn(
        "flex min-w-0 items-start justify-between gap-3 border-b border-border px-3 py-2.5 last:border-0 sm:gap-4 sm:px-4 sm:py-3",
        accent && "bg-timing-rowAlt/50"
      )}
      style={
        accent
          ? ({
              ...style,
              borderLeft: "3px solid color-mix(in srgb, var(--team-accent) 100%, white 15%)",
              background: "color-mix(in srgb, var(--team-accent) 15%, transparent)"
            } as CSSProperties)
          : style
      }
    >
      <div className="min-w-0 flex-1">
        <p className="metadata-label">{label}</p>
        {detail ? <p className="mt-1 text-sm leading-5 text-muted-foreground">{detail}</p> : null}
      </div>
      <div
        className={cn(
          "min-w-0 max-w-[46%] text-right font-mono text-sm font-black leading-5 break-words",
          accent ? "text-[var(--team-accent)]" : trendClassName[trend]
        )}
      >
        {value}
      </div>
    </div>
  );
}
