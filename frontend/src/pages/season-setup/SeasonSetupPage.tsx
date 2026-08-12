import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { seasonRepository } from "@/features/season/api/seasonDataSource";
import { useSeasonStore } from "@/features/season/model/useSeasonStore";
import { formatMoney, getDriver, getTeam } from "@/features/season/lib/seasonViewData";
import { ROUTES } from "@/shared/constants/routes";
import { cn } from "@/shared/lib/utils";
import {
  ActionPanel,
  BudgetPanel,
  Button,
  ButtonLink,
  InfoChip,
  MetricRow,
  PageHeader,
  PageSurface,
  SectionHeader,
  StatusBadge,
  TeamIcon
} from "@/shared/ui";

function getAverage(values: number[]) {
  if (!values.length) {
    return 0;
  }

  return Math.round(values.reduce((total, value) => total + value, 0) / values.length);
}

export function SeasonSetupPage() {
  const selectedTeamId = useSeasonStore((state) => state.selectedTeamId);
  const selectedDriverIds = useSeasonStore((state) => state.selectedDriverIds);
  const budget = useSeasonStore((state) => state.budget);
  const selectTeam = useSeasonStore((state) => state.selectTeam);
  const setDrivers = useSeasonStore((state) => state.setDrivers);
  const confirmRoster = useSeasonStore((state) => state.confirmRoster);
  const isLoading = useSeasonStore((state) => state.isLoading);
  const errorMessage = useSeasonStore((state) => state.errorMessage);
  const navigate = useNavigate();

  const drivers = seasonRepository.getDrivers();
  const teams = seasonRepository.getTeams();
  const activeSeason = seasonRepository.getActiveSeason();
  const persistedTeamId = activeSeason?.selectedTeamId || null;
  const persistedDriverIds = activeSeason?.selectedDriverIds ?? [];
  const isRosterConfirmed = Boolean(
    activeSeason &&
    activeSeason.status !== "setup" &&
    persistedTeamId &&
    persistedDriverIds.length === 2
  );

  useEffect(() => {
    if (isRosterConfirmed) {
      navigate(ROUTES.home, { replace: true });
    }
  }, [isRosterConfirmed, navigate]);

  const activeTeamId = selectedTeamId ?? persistedTeamId ?? "";
  const selectedTeam = getTeam(activeTeamId);
  const selectedDrivers = selectedDriverIds.map(getDriver);
  const hasCatalog = teams.length > 0 && drivers.length > 0;
  const hasSelectedTeam = Boolean(activeTeamId && teams.some((team) => team.id === activeTeamId));
  const hasTwoDrivers = selectedDriverIds.length === 2;
  const hasUniqueDrivers = new Set(selectedDriverIds).size === selectedDriverIds.length;
  const startingBudget = budget.startingMillions;
  const driverCost = selectedDrivers.reduce((total, driver) => total + driver.price, 0);
  const teamCost = hasSelectedTeam ? selectedTeam.price : 0;
  const carBuildCost = hasSelectedTeam ? selectedTeam.carBuildCost * 2 : 0;
  const minimumRepairReserve = hasSelectedTeam ? selectedTeam.minimumRepairReserve : 0;
  const minimumSetupReserve = hasSelectedTeam ? selectedTeam.minimumSetupReserve : 0;
  const minimumReserve = hasSelectedTeam ? selectedTeam.minimumReserve : 0;
  const rosterCost = driverCost + teamCost + carBuildCost;
  const requiredTotal = rosterCost + minimumReserve;
  const previewFreeBudget = startingBudget - requiredTotal;
  const displayedAvailableBudget = isRosterConfirmed
    ? budget.availableMillions
    : startingBudget - rosterCost;
  const displayedRepairReserve = isRosterConfirmed
    ? budget.repairReserveMillions
    : minimumRepairReserve;
  const displayedSetupReserve = isRosterConfirmed
    ? budget.setupReserveMillions
    : minimumSetupReserve;
  const displayedFreeBudget = isRosterConfirmed ? budget.freeMillions : previewFreeBudget;
  const isBudgetValid = requiredTotal <= startingBudget;
  const isRosterValid =
    hasCatalog && hasSelectedTeam && hasTwoDrivers && hasUniqueDrivers && isBudgetValid;
  const averagePace = getAverage(selectedDrivers.map((driver) => driver.pace));
  const averageStability = getAverage(selectedDrivers.map((driver) => driver.stability));
  const validationReasons = [
    !hasCatalog ? "Каталог пилотов и команд еще не загружен." : null,
    !hasSelectedTeam ? "Нужно выбрать одну команду." : null,
    !hasTwoDrivers ? "Нужно выбрать ровно двух пилотов." : null,
    !hasUniqueDrivers ? "Пилоты в составе не должны повторяться." : null,
    !isBudgetValid ? "Стоимость состава превышает доступный стартовый бюджет." : null
  ].filter(Boolean);
  const rosterStatus = isRosterConfirmed
    ? "Состав подтвержден"
    : isRosterValid
      ? "Состав готов к подтверждению"
      : (validationReasons[0] ?? "Состав требует проверки");
  const primaryActionLabel = isRosterConfirmed
    ? "Открыть календарь"
    : isLoading
      ? "Подтверждаем..."
      : "Подтвердить состав";

  function canCompleteRosterWith(candidateId: string) {
    if (!hasSelectedTeam) {
      return false;
    }

    const candidate = getDriver(candidateId);
    const fixedCost = teamCost + carBuildCost + minimumReserve;

    if (selectedDriverIds.length === 0) {
      return drivers.some(
        (other) =>
          other.id !== candidateId && fixedCost + candidate.price + other.price <= startingBudget
      );
    }

    if (selectedDriverIds.length === 1) {
      const firstDriver = getDriver(selectedDriverIds[0]);
      return (
        firstDriver.id !== candidateId &&
        fixedCost + firstDriver.price + candidate.price <= startingBudget
      );
    }

    return false;
  }

  function toggleDriver(driverId: string) {
    if (isRosterConfirmed) {
      return;
    }

    if (selectedDriverIds.includes(driverId)) {
      setDrivers(selectedDriverIds.filter((id) => id !== driverId));
      return;
    }

    if (selectedDriverIds.length < 2 && canCompleteRosterWith(driverId)) {
      setDrivers([...selectedDriverIds, driverId]);
    }
  }

  async function confirmComposition() {
    if (isRosterConfirmed) {
      navigate(ROUTES.seasonOverview);
      return;
    }

    if (!isRosterValid) {
      return;
    }

    try {
      await confirmRoster();
      navigate(ROUTES.seasonOverview);
    } catch {
      // Backend error details are kept in the store and rendered below.
    }
  }

  return (
    <PageSurface>
      <PageHeader
        title="Настройка состава"
        description="Выберите одну команду и ровно двух пилотов из доступного каталога. Перед подтверждением проверьте стоимость заявки, постройку двух болидов и резерв бюджета."
        actions={
          <ButtonLink
            to={isRosterConfirmed ? ROUTES.seasonOverview : ROUTES.home}
            variant="secondary"
          >
            {isRosterConfirmed ? "Календарь" : "Главная"}
          </ButtonLink>
        }
        meta={
          <>
            <InfoChip label="Бюджет" value={formatMoney(startingBudget)} />
            <InfoChip label="Команда" value={hasSelectedTeam ? selectedTeam.shortName : "-"} />
            <InfoChip label="Пилоты" value={`${selectedDriverIds.length}/2`} />
            <InfoChip label="Свободно" value={formatMoney(displayedFreeBudget)} />
          </>
        }
      />

      <section className="grid gap-3 md:grid-cols-5">
        <div className="race-panel p-4">
          <p className="metadata-label">Стартовый бюджет</p>
          <p className="mt-2 timing-value text-2xl">{formatMoney(startingBudget)}</p>
        </div>
        <div className="race-panel p-4">
          <p className="metadata-label">Стоимость заявки</p>
          <p className="mt-2 timing-value text-2xl">{formatMoney(rosterCost)}</p>
        </div>
        <div className="race-panel p-4">
          <p className="metadata-label">Фонд ремонта</p>
          <p className="mt-2 timing-value text-2xl">{formatMoney(displayedRepairReserve)}</p>
        </div>
        <div className="race-panel p-4">
          <p className="metadata-label">Фонд настроек</p>
          <p className="mt-2 timing-value text-2xl">{formatMoney(displayedSetupReserve)}</p>
        </div>
        <div
          className={cn(
            "race-panel p-4",
            isBudgetValid || isRosterConfirmed ? "border-success/40" : "border-danger/40"
          )}
        >
          <p className="metadata-label">Свободные средства</p>
          <p
            className={cn(
              "mt-2 timing-value text-2xl",
              displayedFreeBudget < 0 ? "text-danger" : "text-success"
            )}
          >
            {formatMoney(displayedFreeBudget)}
          </p>
        </div>
      </section>

      {isRosterConfirmed ? (
        <section className="border border-success/35 bg-success/10 p-5 shadow-insetLine">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-black uppercase tracking-[0.2em] text-success">
                Состав зафиксирован
              </p>
              <p className="mt-3 max-w-3xl text-sm leading-6 text-foreground">
                Состав уже подтвержден для текущей сессии. Этот экран остается протоколом состава, а
                следующий рабочий шаг находится в календаре сезона.
              </p>
            </div>
            <ButtonLink to={ROUTES.seasonOverview}>Открыть календарь</ButtonLink>
          </div>
        </section>
      ) : null}

      <div className="grid min-w-0 gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(330px,400px)]">
        <section className="min-w-0 space-y-5">
          <section className="space-y-3">
            <SectionHeader
              title="1. Команда"
              description="Команда задает стоимость заявки, рейтинг болида, надежность и цену постройки двух болидов."
            />
            <div className="race-panel divide-y divide-border overflow-hidden">
              {teams.map((team) => {
                const isSelected = team.id === activeTeamId;

                return (
                  <button
                    key={team.id}
                    aria-pressed={isSelected}
                    className={cn(
                      "grid w-full gap-4 px-4 py-3 text-left transition hover:bg-muted/25 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background md:grid-cols-[1fr_82px_100px_92px_150px]",
                      isSelected && "bg-primary/10 shadow-insetLine",
                      isRosterConfirmed && "cursor-not-allowed"
                    )}
                    disabled={isRosterConfirmed}
                    type="button"
                    onClick={() => selectTeam(team.id)}
                  >
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-3">
                        <TeamIcon className="size-5" color={team.color} teamId={team.id} />
                        <h3 className="text-base font-black uppercase text-foreground">
                          {team.shortName}
                        </h3>
                        <StatusBadge variant={isSelected ? "live" : "neutral"}>
                          {isSelected ? "Выбрана" : "Доступна"}
                        </StatusBadge>
                      </div>
                      <p className="mt-1 text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">
                        {team.powerUnit} / {team.baseCountry}
                      </p>
                    </div>
                    <div>
                      <p className="metadata-label">Заявка</p>
                      <p className="mt-1 timing-value">{formatMoney(team.price)}</p>
                    </div>
                    <div>
                      <p className="metadata-label">Рейтинг болида</p>
                      <p className="mt-1 timing-value">{team.carRating}</p>
                    </div>
                    <div>
                      <p className="metadata-label">2 болида</p>
                      <p className="mt-1 timing-value">{formatMoney(team.carBuildCost * 2)}</p>
                    </div>
                    <div>
                      <p className="metadata-label">Резервы</p>
                      <p className="mt-1 text-xs font-bold text-foreground">
                        Ремонт {formatMoney(team.minimumRepairReserve)}
                      </p>
                      <p className="mt-1 text-xs font-bold text-muted-foreground">
                        Настройки {formatMoney(team.minimumSetupReserve)}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>
          </section>

          <section className="space-y-3">
            <SectionHeader
              title="2. Пилоты"
              description="Нужно ровно два пилота. Уже выбранного пилота можно снять повторным нажатием, пока состав не подтвержден."
            />
            <div className="grid gap-3 md:grid-cols-2">
              {[0, 1].map((slotIndex) => {
                const driver = selectedDrivers[slotIndex];

                return (
                  <div
                    key={slotIndex}
                    className={cn(
                      "race-panel p-4",
                      driver ? "border-primary/50 bg-primary/10" : "border-dashed"
                    )}
                  >
                    <p className="metadata-label">Слот {slotIndex + 1}</p>
                    <p className="mt-2 text-lg font-black uppercase text-foreground">
                      {driver ? `${driver.firstName} ${driver.lastName}` : "Пусто"}
                    </p>
                    <p className="mt-1 text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">
                      {driver
                        ? `${driver.code} / темп ${driver.pace} / стабильность ${driver.stability} / ${formatMoney(driver.price)}`
                        : "Выберите пилота из списка ниже"}
                    </p>
                  </div>
                );
              })}
            </div>

            <div className="race-panel divide-y divide-border overflow-hidden">
              {drivers.map((driver) => {
                const isSelected = selectedDriverIds.includes(driver.id);
                const slotsAreFull = !isSelected && selectedDriverIds.length >= 2;
                const fitsBudget = isSelected || canCompleteRosterWith(driver.id);
                const isUnavailable =
                  !isSelected && (!hasSelectedTeam || slotsAreFull || !fitsBudget);
                const isInvalidSelectedDriver = isSelected && hasTwoDrivers && !isBudgetValid;
                const statusLabel = isSelected
                  ? isInvalidSelectedDriver
                    ? "Не укладывается"
                    : "В составе"
                  : !hasSelectedTeam
                    ? "Сначала выберите команду"
                    : slotsAreFull
                      ? "Слоты заняты"
                      : !fitsBudget
                        ? "Недоступен по бюджету"
                        : "Выбрать";

                return (
                  <button
                    key={driver.id}
                    aria-pressed={isSelected}
                    className={cn(
                      "grid w-full gap-4 px-4 py-3 text-left transition hover:bg-muted/25 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background md:grid-cols-[1fr_78px_92px_92px]",
                      isSelected && !isInvalidSelectedDriver && "bg-primary/10 shadow-insetLine",
                      isInvalidSelectedDriver && "border-danger/50 bg-danger/10 shadow-insetLine",
                      (isUnavailable || isRosterConfirmed) &&
                        "cursor-not-allowed opacity-55 hover:bg-transparent"
                    )}
                    disabled={isUnavailable || isRosterConfirmed}
                    type="button"
                    onClick={() => toggleDriver(driver.id)}
                  >
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-3">
                        <h3 className="text-base font-black uppercase text-foreground">
                          {driver.firstName} {driver.lastName}
                        </h3>
                        <StatusBadge
                          variant={
                            isInvalidSelectedDriver
                              ? "danger"
                              : isSelected
                                ? "completed"
                                : isUnavailable
                                  ? "scheduled"
                                  : "neutral"
                          }
                        >
                          {statusLabel}
                        </StatusBadge>
                      </div>
                      <p className="mt-1 text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">
                        #{driver.number} {driver.code} / {driver.nationality}
                      </p>
                    </div>
                    <div>
                      <p className="metadata-label">Темп</p>
                      <p className="mt-1 timing-value">{driver.pace}</p>
                    </div>
                    <div>
                      <p className="metadata-label">Стаб.</p>
                      <p className="mt-1 timing-value">{driver.stability}</p>
                    </div>
                    <div>
                      <p className="metadata-label">Цена</p>
                      <p className="mt-1 timing-value">{formatMoney(driver.price)}</p>
                    </div>
                  </button>
                );
              })}
            </div>
          </section>
        </section>

        <aside className="min-w-0 space-y-4 xl:sticky xl:top-6 xl:self-start">
          <SectionHeader
            title="Проверка состава"
            description="Финальный протокол перед сохранением данных: команда, два пилота и бюджет без отрицательного остатка."
          />
          <div
            className={cn(
              "race-panel p-4",
              isRosterValid || isRosterConfirmed
                ? "border-success/40 bg-success/10"
                : hasTwoDrivers && !isBudgetValid
                  ? "border-danger/40 bg-danger/10"
                  : "border-warning/40 bg-warning/10"
            )}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="metadata-label">Статус</p>
                <p className="mt-2 text-lg font-black uppercase text-foreground">{rosterStatus}</p>
              </div>
              <StatusBadge
                variant={
                  isRosterValid || isRosterConfirmed
                    ? "success"
                    : hasTwoDrivers && !isBudgetValid
                      ? "danger"
                      : "warning"
                }
              >
                {isRosterValid || isRosterConfirmed ? "Валиден" : "Проверка"}
              </StatusBadge>
            </div>
            <div className="mt-4 border-t border-border pt-2">
              <MetricRow
                label="Команда"
                value={hasSelectedTeam ? selectedTeam.shortName : "-"}
                detail={
                  hasSelectedTeam
                    ? `${selectedTeam.powerUnit} / ${selectedTeam.baseCountry}`
                    : "Не выбрана"
                }
              />
              <MetricRow
                label="Пилоты"
                value={`${selectedDriverIds.length}/2`}
                detail={
                  selectedDrivers.length
                    ? selectedDrivers
                        .map((driver) => `${driver.firstName} ${driver.lastName}`)
                        .join(" / ")
                    : "Нужны два пилота"
                }
              />
              <MetricRow
                label="Средний темп"
                value={selectedDrivers.length ? averagePace : "-"}
                detail="По выбранным пилотам"
              />
              <MetricRow
                label="Средняя стабильность"
                value={selectedDrivers.length ? averageStability : "-"}
                detail="Риск ошибок и сходов"
              />
              <MetricRow
                label="Свободные средства"
                value={formatMoney(displayedFreeBudget)}
                detail={
                  isBudgetValid || isRosterConfirmed
                    ? "Состав укладывается в бюджет"
                    : "Стоимость выше лимита"
                }
                trend={isBudgetValid || isRosterConfirmed ? "up" : "down"}
              />
            </div>
          </div>

          <BudgetPanel
            title="Бюджетный протокол"
            overview={[
              {
                label: "Бюджет",
                value: formatMoney(startingBudget)
              },
              {
                label: "Заявка",
                value: formatMoney(rosterCost)
              },
              {
                label: "Ремонт",
                value: formatMoney(displayedRepairReserve)
              },
              {
                label: "Настройки",
                value: formatMoney(displayedSetupReserve)
              },
              {
                label: "Свободно",
                value: formatMoney(displayedFreeBudget),
                emphasis:
                  displayedFreeBudget < 0
                    ? "danger"
                    : displayedFreeBudget <= startingBudget * 0.15
                      ? "warning"
                      : "success"
              }
            ]}
            lines={[
              {
                label: "Пилоты",
                value: formatMoney(driverCost),
                detail: "Сумма цен выбранных пилотов",
                trend: "down"
              },
              {
                label: "Командная заявка",
                value: formatMoney(teamCost),
                detail: hasSelectedTeam ? selectedTeam.shortName : "Команда не выбрана",
                trend: "down"
              },
              {
                label: "Постройка 2 болидов",
                value: formatMoney(carBuildCost),
                detail: hasSelectedTeam
                  ? `${formatMoney(selectedTeam.carBuildCost)} за болид`
                  : "Команда не выбрана",
                trend: "down"
              }
            ]}
            summary={{
              label: "Доступно всего",
              value: formatMoney(displayedAvailableBudget),
              detail: isRosterConfirmed
                ? "Все неистраченные деньги: фонды ремонта и настроек плюс свободная часть."
                : "Остаток после заявки до разделения на обязательные фонды и свободные деньги."
            }}
          />
        </aside>
      </div>

      <ActionPanel
        title={isRosterConfirmed ? "Состав подтвержден" : "Подтвердить состав"}
        description={
          isRosterConfirmed
            ? "Выбранная команда, два пилота, бюджет и болиды зафиксированы. Продолжайте сезон через календарь."
            : isRosterValid
              ? `${selectedTeam.shortName}: ${selectedDrivers
                  .map((driver) => `${driver.firstName} ${driver.lastName}`)
                  .join(
                    " / "
                  )}. После подтверждения система сохранит состав, создаст болиды и откроет календарь сезона.`
              : validationReasons.join(" ")
        }
      >
        {errorMessage ? (
          <p className="border border-danger/40 bg-danger/10 px-3 py-2 text-sm font-bold text-danger">
            {errorMessage}
          </p>
        ) : null}
        <Button
          disabled={(!isRosterConfirmed && !isRosterValid) || isLoading}
          type="button"
          onClick={confirmComposition}
        >
          {primaryActionLabel}
        </Button>
        <ButtonLink to={ROUTES.home} variant="secondary">
          Главная
        </ButtonLink>
      </ActionPanel>
    </PageSurface>
  );
}
