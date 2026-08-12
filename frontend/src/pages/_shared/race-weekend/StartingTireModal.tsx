import { useEffect, useState } from "react";
import type { TireCompound } from "@/entities";
import { formatDriverName } from "@/features/season/lib/seasonViewData";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui";
import { compoundLabels } from "@/pages/_shared/race-weekend/raceWeekendUtils";

const tireCompounds: TireCompound[] = ["Soft", "Medium", "Hard", "Intermediate", "Wet"];

export function StartingTireModal({
  isOpen,
  onClose,
  onConfirm,
  drivers,
  recommendedStartingCompound
}: {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (tires: Record<string, string>) => void;
  drivers: string[];
  recommendedStartingCompound?: TireCompound | null;
}) {
  const recommendedTire = recommendedStartingCompound ?? "Medium";
  const [selections, setSelections] = useState<Record<string, string>>(() =>
    Object.fromEntries(drivers.map((id) => [id, recommendedTire]))
  );

  useEffect(() => {
    if (!isOpen) return;
    setSelections(Object.fromEntries(drivers.map((id) => [id, recommendedTire])));
  }, [drivers, isOpen, recommendedTire]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 p-4 backdrop-blur-sm">
      <div className="w-full max-w-md border border-line bg-secondary p-6 font-mono uppercase shadow-2xl">
        <h2 className="text-lg font-black tracking-tighter">Шинная стратегия</h2>
        <p className="mt-2 text-xs text-muted-foreground">Выберите тип шин для старта гонки</p>

        <div className="mt-6 space-y-6">
          {drivers.map((driverId) => (
            <div key={driverId} className="space-y-2">
              <label className="text-[10px] font-black text-muted-foreground">
                Пилот: {formatDriverName(driverId)}
              </label>
              <div className="grid grid-cols-5 gap-2">
                {tireCompounds.map((compound) => (
                  <button
                    key={compound}
                    aria-pressed={selections[driverId] === compound}
                    onClick={() =>
                      setSelections((prev: Record<string, string>) => ({
                        ...prev,
                        [driverId]: compound
                      }))
                    }
                    className={cn(
                      "min-w-0 border px-1 py-2 text-[10px] font-black transition-colors",
                      selections[driverId] === compound
                        ? "border-primary bg-primary text-primary-foreground"
                        : compound === recommendedTire
                          ? "border-success/70 bg-surface text-foreground hover:border-primary/50"
                          : "border-line bg-surface text-muted-foreground hover:border-primary/50"
                    )}
                  >
                    {compoundLabels[compound]}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-8 flex gap-3">
          <Button variant="secondary" className="flex-1" onClick={onClose}>
            Отмена
          </Button>
          <Button className="flex-1" onClick={() => onConfirm(selections)}>
            В бой!
          </Button>
        </div>
      </div>
    </div>
  );
}
