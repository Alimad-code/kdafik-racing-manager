import type { Driver } from "@/entities";
import { StatusBadge, type StatusBadgeVariant } from "@/shared/ui/StatusBadge";

type DriverSummaryProps = {
  driver: Driver;
  role: string;
  slotCode?: string;
  status?: {
    label: string;
    variant: StatusBadgeVariant;
  };
};

export function DriverSummary({ driver, role, slotCode, status }: DriverSummaryProps) {
  return (
    <article className="race-panel border-l-2 border-l-primary/70 p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            {slotCode ? (
              <span className="timing-value text-sm text-primary">{slotCode}</span>
            ) : null}
            <p className="metadata-label">{role}</p>
          </div>
          <h3 className="mt-2 text-xl font-black uppercase text-foreground">
            {driver.firstName} {driver.lastName}
          </h3>
          <p className="mt-1 font-mono text-sm font-bold text-muted-foreground">
            #{driver.number} / {driver.code} / {driver.nationality}
          </p>
        </div>
        {status ? <StatusBadge variant={status.variant}>{status.label}</StatusBadge> : null}
      </div>
      <div className="mt-5 grid grid-cols-3 gap-3 border-t border-border pt-4">
        <div>
          <p className="metadata-label">Код</p>
          <p className="mt-1 timing-value text-xl">{driver.code}</p>
        </div>
        <div>
          <p className="metadata-label">Темп</p>
          <p className="mt-1 timing-value text-xl">{driver.pace}</p>
        </div>
        <div>
          <p className="metadata-label">Цена</p>
          <p className="mt-1 timing-value text-xl">${driver.price.toFixed(1)}M</p>
        </div>
      </div>
    </article>
  );
}
