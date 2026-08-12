import { formatMoney, getDriver, getTeam } from "@/features/season/lib/seasonViewData";
import { useSeasonStore } from "@/features/season/model/useSeasonStore";
import { Button } from "@/shared/ui/Button";
import { StatusBadge } from "@/shared/ui/StatusBadge";

const labels = {
  healthy: "Исправен",
  damaged: "Повреждён",
  "heavily-damaged": "Сильные повреждения"
} as const;

export function CarConditionPanel() {
  const cars = useSeasonStore((state) => state.cars);
  const selectedTeamId = useSeasonStore((state) => state.selectedTeamId);
  const budget = useSeasonStore((state) => state.budget);
  const repairCar = useSeasonStore((state) => state.repairCar);
  const isLoading = useSeasonStore((state) => state.isLoading);
  const team = selectedTeamId ? getTeam(selectedTeamId) : null;

  const hasDamagedCar = cars.some(
    (car) => car.condition === "damaged" || car.condition === "heavily-damaged"
  );

  if (!team || !hasDamagedCar) return null;

  const availableForRepair = budget.repairReserveMillions + budget.freeMillions;

  return (
    <section className="race-panel overflow-hidden">
      <div className="border-b border-line px-4 py-3">
        <p className="metadata-label">Состояние болидов</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Повреждённый болид может продолжать этап со штрафом к темпу и риску. Сильно повреждённый
          нужно отремонтировать до следующей сессии.
        </p>
      </div>
      <div className="grid divide-y divide-line md:grid-cols-2 md:divide-x md:divide-y-0">
        {cars.map((car) => {
          const driver = getDriver(car.driverId);
          const cost = team.repairCost * (car.condition === "heavily-damaged" ? 2 : 1);
          const canRepair = car.condition !== "healthy" && availableForRepair >= cost;
          const repairLabel = canRepair
            ? `Ремонт ${driver.firstName} ${driver.lastName}: ${formatMoney(cost)}`
            : `Недостаточно средств для ремонта ${driver.firstName} ${driver.lastName}`;
          const detail =
            car.condition === "healthy"
              ? `Надёжность ${car.reliability}`
              : car.condition === "damaged"
                ? "Можно продолжать: темп ниже, риск происшествия выше."
                : "Следующая сессия заблокирована до ремонта.";

          return (
            <div key={car.id} className="flex items-center justify-between gap-4 px-4 py-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-black uppercase text-foreground">
                  {driver.firstName} {driver.lastName}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <StatusBadge
                  variant={
                    car.condition === "healthy"
                      ? "success"
                      : car.condition === "damaged"
                        ? "warning"
                        : "danger"
                  }
                >
                  {labels[car.condition]}
                </StatusBadge>
                {car.condition !== "healthy" ? (
                  <Button
                    aria-label={repairLabel}
                    disabled={isLoading || !canRepair}
                    title={
                      canRepair
                        ? `Ремонт: ${formatMoney(cost)}`
                        : `Нужно ${formatMoney(cost)} из фонда ремонта и свободных денег`
                    }
                    type="button"
                    variant="secondary"
                    onClick={() => void repairCar(car.id).catch(() => undefined)}
                  >
                    {canRepair ? `Ремонт ${formatMoney(cost)}` : "Недостаточно средств"}
                  </Button>
                ) : null}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
