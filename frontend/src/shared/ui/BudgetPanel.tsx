import { MetricRow } from "@/shared/ui/MetricRow";

type BudgetLine = {
  label: string;
  value: string;
  detail?: string;
  trend?: "up" | "down" | "flat";
};

type BudgetOverviewItem = {
  label: string;
  value: string;
  emphasis?: "default" | "success" | "danger" | "warning";
};

type BudgetPanelProps = {
  overview: BudgetOverviewItem[];
  lines: BudgetLine[];
  title?: string;
  summary?: {
    label: string;
    value: string;
    detail: string;
  };
};

export function BudgetPanel({
  overview,
  lines,
  title = "Бюджет сезона",
  summary
}: BudgetPanelProps) {
  const emphasisClassName: Record<NonNullable<BudgetOverviewItem["emphasis"]>, string> = {
    default: "mt-1 timing-value text-xl",
    success: "mt-1 timing-value text-xl text-success",
    danger: "mt-1 timing-value text-xl text-danger",
    warning: "mt-1 timing-value text-xl text-warning"
  };

  return (
    <section className="race-panel">
      <div className="border-b border-border p-4">
        <p className="metadata-label">{title}</p>
        <div className="mt-4 grid grid-cols-3 gap-3">
          {overview.map((item) => (
            <div key={item.label}>
              <p className="metadata-label">{item.label}</p>
              <p className={emphasisClassName[item.emphasis ?? "default"]}>{item.value}</p>
            </div>
          ))}
        </div>
      </div>
      {lines.map((line) => (
        <MetricRow
          key={line.label}
          label={line.label}
          value={line.value}
          detail={line.detail}
          trend={line.trend}
        />
      ))}
      {summary ? (
        <div className="border-t border-primary/40 bg-primary/10 p-4">
          <p className="metadata-label">{summary.label}</p>
          <p className="mt-2 timing-value text-3xl">{summary.value}</p>
          <p className="mt-2 text-sm text-muted-foreground">{summary.detail}</p>
        </div>
      ) : null}
    </section>
  );
}
