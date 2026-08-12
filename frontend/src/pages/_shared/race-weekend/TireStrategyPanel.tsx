import { Gauge } from "lucide-react";
import type { TireCompound, TireStrategy } from "@/entities";
import { compoundLabels } from "@/pages/_shared/race-weekend/raceWeekendUtils";
import { cn } from "@/shared/lib/utils";

interface TireStrategyPanelProps {
  strategies?: TireStrategy[] | null;
  totalLaps: number;
}

const compoundClasses: Record<TireCompound, string> = {
  Soft: "border-danger/70 bg-danger/20 text-danger",
  Medium: "border-warning/70 bg-warning/20 text-warning",
  Hard: "border-slate-300/50 bg-slate-200/15 text-slate-200",
  Intermediate: "border-sky-400/70 bg-sky-400/20 text-sky-300",
  Wet: "border-blue-500/70 bg-blue-500/25 text-blue-300"
};

export function TireStrategyPanel({ strategies, totalLaps }: TireStrategyPanelProps) {
  return (
    <section
      className="shrink-0 border-b border-line bg-background/35 px-4 py-3 font-mono uppercase shadow-insetLine"
      data-testid="tire-strategy-panel"
      aria-labelledby="tire-strategy-title"
    >
      <div className="mb-2 flex items-center justify-between gap-3">
        <h2
          id="tire-strategy-title"
          className="text-[11px] font-black tracking-[0.22em] text-foreground"
        >
          Возможные стратегии
        </h2>
      </div>

      {strategies?.length ? (
        <div className="grid gap-2">
          {strategies.map((strategy) => (
            <article
              key={strategy.number}
              className="grid grid-cols-[88px_minmax(0,1fr)] items-center gap-3"
              data-testid={`tire-strategy-${strategy.number}`}
            >
              <div>
                <strong className="block text-[10px] font-black text-foreground">
                  Стратегия {strategy.number}
                </strong>
                <span className="text-[9px] font-bold text-muted-foreground">
                  {strategy.pitStopCount} пит
                </span>
              </div>
              <div
                className="flex min-w-0"
                aria-label={`Стратегия ${strategy.number}`}
                data-testid={`tire-strategy-${strategy.number}-bar`}
              >
                {strategy.stints.map((stint, index) => {
                  const lapCount = stint.endLap - stint.startLap + 1;
                  const hasPitWindow = index < strategy.stints.length - 1;
                  return (
                    <div
                      key={`${stint.compound}-${stint.startLap}-${stint.endLap}`}
                      className="relative min-w-0"
                      style={{ width: `${(lapCount / Math.max(1, totalLaps)) * 100}%` }}
                      data-testid={`tire-strategy-${strategy.number}-stint-${index + 1}`}
                    >
                      <div
                        className={cn(
                          "flex h-8 min-w-0 items-center justify-center border-y border-l px-1 text-[9px] font-black last:border-r",
                          compoundClasses[stint.compound]
                        )}
                        title={`${compoundLabels[stint.compound]}: круги ${stint.startLap}–${stint.endLap}`}
                      >
                        <span className="truncate">
                          {compoundLabels[stint.compound]} · {stint.startLap}–{stint.endLap}
                        </span>
                      </div>
                      {hasPitWindow &&
                      stint.pitWindowStartLap != null &&
                      stint.pitWindowEndLap != null ? (
                        <span
                          className="absolute -right-3 top-1/2 z-10 flex -translate-y-1/2 items-center gap-0.5 border border-line bg-secondary px-1 py-0.5 text-[8px] font-black text-foreground shadow-lg"
                          title={`Пит-окно: круги ${stint.pitWindowStartLap}–${stint.pitWindowEndLap}`}
                          data-testid={`tire-strategy-${strategy.number}-pit-window-${index + 1}`}
                        >
                          <Gauge className="size-2.5" aria-hidden="true" />
                          {stint.pitWindowStartLap}–{stint.pitWindowEndLap}
                        </span>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            </article>
          ))}
        </div>
      ) : (
        <p className="border border-line bg-secondary px-3 py-2 text-[10px] font-bold text-muted-foreground">
          Расчёт стратегии недоступен
        </p>
      )}
    </section>
  );
}
