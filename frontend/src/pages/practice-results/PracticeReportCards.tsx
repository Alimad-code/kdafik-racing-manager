import type { CSSProperties } from "react";
import type { PracticeResult } from "@/entities";
import { formatDriverName, getTeam } from "@/features/season/lib/seasonViewData";
import { getReadableTeamAccent } from "@/shared/lib/teamAccent";
import { TeamIcon } from "@/shared/ui";

const REPORT_LABELS = ["Аэродинамика", "Шасси", "Трансмиссия"] as const;

type PracticeReportCardsProps = {
  rows: PracticeResult[];
  driverIds: string[];
};

function parseSetupFeedback(feedback?: string) {
  if (!feedback?.trim()) {
    return null;
  }

  const assessments = new Map(
    feedback
      .split(/\r?\n/)
      .map((line) => line.split(/:\s*/, 2))
      .filter((parts): parts is [string, string] => parts.length === 2 && Boolean(parts[1]?.trim()))
      .map(([label, value]) => [label.trim(), value.trim()])
  );

  if (!REPORT_LABELS.every((label) => assessments.has(label))) {
    return null;
  }

  return REPORT_LABELS.map((label) => ({
    label,
    value: assessments.get(label) ?? ""
  }));
}

export function PracticeReportCards({ rows, driverIds }: PracticeReportCardsProps) {
  return (
    <section aria-labelledby="practice-reports-title" className="space-y-3">
      <div className="grid gap-3 lg:grid-cols-2">
        {driverIds.slice(0, 2).map((driverId, index) => {
          const result = rows.find((row) => row.driverId === driverId);
          const assessments = parseSetupFeedback(result?.setupFeedback);
          const recommendation = result?.engineerRecommendation?.trim();
          const hasReport = Boolean(assessments && recommendation);
          const team = result ? getTeam(result.teamId) : undefined;

          return (
            <article
              key={driverId}
              data-testid={`practice-report-driver-${index + 1}`}
              className="relative min-w-0 overflow-hidden border border-border bg-card p-4"
              style={
                team
                  ? ({
                      borderLeftColor: getReadableTeamAccent(team.color),
                      borderLeftWidth: "3px"
                    } as CSSProperties)
                  : undefined
              }
            >
              <header className="mb-4 flex min-w-0 items-center gap-3 border-b border-border pb-3">
                {team && (
                  <TeamIcon className="size-5 shrink-0" color={team.color} teamId={team.id} />
                )}
                <div className="min-w-0">
                  <p className="font-mono text-[10px] font-bold tracking-[0.18em] text-muted-foreground uppercase">
                    Пилот {index + 1}
                  </p>
                  <h3 className="truncate text-base font-black text-foreground uppercase">
                    {formatDriverName(driverId)}
                  </h3>
                </div>
              </header>

              {hasReport && assessments ? (
                <>
                  <dl className="space-y-2.5">
                    {assessments.map(({ label, value }) => (
                      <div key={label} className="grid gap-1 sm:grid-cols-[8rem_minmax(0,1fr)]">
                        <dt className="font-mono text-[10px] font-bold tracking-[0.12em] text-muted-foreground uppercase">
                          {label}
                        </dt>
                        <dd className="text-sm leading-snug text-foreground">{value}</dd>
                      </div>
                    ))}
                  </dl>
                  <div className="mt-4 border-t border-border pt-3">
                    <p className="font-mono text-[10px] font-bold tracking-[0.14em] text-primary uppercase">
                      Главный приоритет
                    </p>
                    <p className="mt-1 text-sm leading-snug text-foreground">{recommendation}</p>
                  </div>
                </>
              ) : (
                <p className="py-6 text-sm text-muted-foreground">Отчёт недоступен</p>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
