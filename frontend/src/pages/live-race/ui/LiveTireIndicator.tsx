import { cn } from "@/shared/lib/utils";
import { compoundShortLabels, compoundTextClassName, liveTireLabels } from "./liveTires";

export function LiveTireIndicator({ compound }: { compound?: string }) {
  if (!compound) return <span className="text-muted-foreground">-</span>;

  return (
    <span
      aria-label={liveTireLabels[compound] ?? compound}
      className={cn(
        "font-mono text-sm font-black uppercase leading-none",
        compoundTextClassName[compound] ?? "text-muted-foreground"
      )}
      title={liveTireLabels[compound] ?? compound}
    >
      {compoundShortLabels[compound] ?? compound.slice(0, 1)}
    </span>
  );
}
