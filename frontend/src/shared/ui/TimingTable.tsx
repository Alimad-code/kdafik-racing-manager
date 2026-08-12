import type { CSSProperties, ReactNode } from "react";
import { cn } from "@/shared/lib/utils";

type TimingTableDensity = "compact" | "normal";

export type TimingTableColumn<Row> = {
  key: string;
  header: ReactNode;
  align?: "left" | "right" | "center";
  headerClassName?: string;
  cellClassName?: string;
  render: (row: Row, index: number) => ReactNode;
};

type TimingTableProps<Row> = {
  columns: TimingTableColumn<Row>[];
  rows: Row[];
  getRowKey: (row: Row, index: number) => string;
  caption?: string;
  density?: TimingTableDensity;
  emptyMessage?: string;
  getRowClassName?: (row: Row, index: number) => string | undefined;
  getRowStyle?: (row: Row, index: number) => CSSProperties | undefined;
};

const alignClassName = {
  left: "text-left",
  right: "text-right",
  center: "text-center"
};

const densityClassName: Record<TimingTableDensity, string> = {
  compact: "px-2 py-1.5 sm:px-3 sm:py-2",
  normal: "px-3 py-2 sm:px-4 sm:py-3"
};

export function TimingTable<Row>({
  columns,
  rows,
  getRowKey,
  caption,
  density = "normal",
  emptyMessage = "Нет данных классификации.",
  getRowClassName,
  getRowStyle
}: TimingTableProps<Row>) {
  return (
    <div className="max-w-full overflow-x-auto border border-border bg-timing-surface shadow-insetLine">
      <table className="w-full min-w-max border-collapse text-xs sm:text-sm">
        {caption ? (
          <caption className="border-b border-border bg-surface-track px-3 py-2 text-left metadata-label sm:px-4 sm:py-3">
            {caption}
          </caption>
        ) : null}
        <thead>
          <tr className="border-b border-border bg-timing-header">
            {columns.map((column) => (
              <th
                key={column.key}
                className={cn(
                  "whitespace-nowrap font-mono text-[10px] font-black uppercase tracking-[0.12em] text-muted-foreground sm:text-[11px] sm:tracking-[0.16em]",
                  densityClassName[density],
                  alignClassName[column.align ?? "left"],
                  column.headerClassName
                )}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td
                className="px-3 py-6 text-center text-sm text-muted-foreground sm:px-4 sm:py-8"
                colSpan={columns.length}
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            rows.map((row, rowIndex) => {
              const rowStyle = getRowStyle?.(row, rowIndex);
              const hasAccent = Boolean(
                rowStyle && (rowStyle as Record<string, unknown>)["--team-accent"]
              );

              return (
                <tr
                  key={getRowKey(row, rowIndex)}
                  className={cn(
                    "border-b border-border/70 bg-timing-row transition last:border-0 hover:bg-muted/40",
                    !hasAccent && "odd:bg-timing-rowAlt",
                    hasAccent && "row-team-accent",
                    getRowClassName?.(row, rowIndex)
                  )}
                  style={rowStyle}
                >
                  {columns.map((column) => (
                    <td
                      key={column.key}
                      className={cn(
                        "whitespace-nowrap text-muted-foreground",
                        densityClassName[density],
                        alignClassName[column.align ?? "left"],
                        column.cellClassName
                      )}
                    >
                      {column.render(row, rowIndex)}
                    </td>
                  ))}
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}
