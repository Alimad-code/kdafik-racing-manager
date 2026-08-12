import type { ReactNode } from "react";
import { cn } from "@/shared/lib/utils";

export type StatusBadgeVariant =
  | "neutral"
  | "success"
  | "warning"
  | "danger"
  | "info"
  | "live"
  | "scheduled"
  | "completed"
  | "retired";

const variantClassName: Record<StatusBadgeVariant, string> = {
  neutral: "border-border bg-secondary text-muted-foreground",
  success: "border-success/40 bg-success/10 text-success",
  warning: "border-warning/40 bg-warning/10 text-warning",
  danger: "border-danger/40 bg-danger/10 text-danger",
  info: "border-info/40 bg-info/10 text-info",
  live: "border-primary/50 bg-primary/15 text-primary",
  scheduled: "border-info/35 bg-info/10 text-info",
  completed: "border-success/35 bg-success/10 text-success",
  retired: "border-danger/45 bg-danger/10 text-danger"
};

type StatusBadgeProps = {
  children: ReactNode;
  variant?: StatusBadgeVariant;
};

export function StatusBadge({ children, variant = "neutral" }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center border px-2.5 py-1 font-mono text-[11px] font-bold uppercase tracking-[0.12em] shadow-insetLine",
        variantClassName[variant]
      )}
    >
      {children}
    </span>
  );
}
