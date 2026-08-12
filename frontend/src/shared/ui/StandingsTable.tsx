import type { CSSProperties } from "react";
import { getReadableTeamAccent } from "@/shared/lib/teamAccent";
import { TeamIcon } from "@/shared/ui/TeamIcon";
import { TimingTable } from "@/shared/ui/TimingTable";

export type StandingsTableRow = {
  position: number;
  participantId?: string;
  label: string;
  teamId?: string;
  teamName?: string;
  points: number;
  delta?: string;
  isHighlighted?: boolean;
  accent?: string;
};

type StandingsTableProps = {
  rows: StandingsTableRow[];
  caption?: string;
};

const FALLBACK_TEAM_COLOR = "#64748b";

export function StandingsTable({ rows, caption = "Таблица чемпионата" }: StandingsTableProps) {
  const showTeamIconColumn = rows.some((row) => row.teamId);
  const showTeamNameColumn = rows.some((row) => row.teamName);

  return (
    <TimingTable
      caption={caption}
      density="compact"
      rows={rows}
      getRowKey={(row) => `${row.position}-${row.label}`}
      getRowClassName={(row) =>
        row.isHighlighted ? undefined : row.position === 1 ? "bg-success/5" : undefined
      }
      getRowStyle={(row) =>
        row.isHighlighted
          ? ({
              "--team-accent": getReadableTeamAccent(row.accent || FALLBACK_TEAM_COLOR)
            } as CSSProperties)
          : undefined
      }
      columns={[
        {
          key: "position",
          header: "Поз",
          headerClassName: "w-10",
          cellClassName: "w-10",
          render: (row) => <span className="timing-value text-base">{row.position}</span>
        },
        {
          key: "label",
          header: "Участник",
          render: (row) => <p className="font-bold text-foreground">{row.label}</p>
        },
        ...(showTeamIconColumn
          ? [
              {
                key: "team-icon",
                header: <span className="sr-only">Эмблема команды</span>,
                headerClassName: "w-9",
                cellClassName: "w-9",
                render: (row: StandingsTableRow) => (
                  <TeamIcon
                    className="size-4"
                    color={row.accent || FALLBACK_TEAM_COLOR}
                    teamId={row.teamId}
                  />
                )
              }
            ]
          : []),
        ...(showTeamNameColumn
          ? [
              {
                key: "team",
                header: "Команда",
                render: (row: StandingsTableRow) => (
                  <span className="font-semibold text-foreground">{row.teamName}</span>
                )
              }
            ]
          : []),
        {
          key: "delta",
          header: "Отрыв",
          align: "right",
          render: (row) => <span className="font-mono text-xs">{row.delta ?? "-"}</span>
        },
        {
          key: "points",
          header: "Очк",
          align: "right",
          render: (row) => <span className="timing-value text-base">{row.points}</span>
        }
      ]}
    />
  );
}
