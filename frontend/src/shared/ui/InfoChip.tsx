import type { ReactNode } from "react";

type InfoChipProps = {
  label: string;
  value: ReactNode;
};

export function InfoChip({ label, value }: InfoChipProps) {
  return (
    <span className="inline-flex max-w-full min-w-0 items-center gap-1.5 border border-border bg-secondary px-2.5 py-1 text-[11px] shadow-insetLine sm:gap-2 sm:px-3 sm:py-1.5 sm:text-xs">
      <span className="shrink-0 font-semibold uppercase tracking-[0.14em] text-muted-foreground sm:tracking-[0.16em]">
        {label}
      </span>
      <span className="min-w-0 truncate font-mono font-bold text-foreground">{value}</span>
    </span>
  );
}
