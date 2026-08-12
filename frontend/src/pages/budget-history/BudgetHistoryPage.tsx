import { formatMoney } from "@/features/season/lib/seasonViewData";
import { useSeasonStore } from "@/features/season/model/useSeasonStore";
import { ROUTES } from "@/shared/constants/routes";
import { ButtonLink, PageHeader, PageSurface, SectionHeader, StatBlock } from "@/shared/ui";

const CATEGORY_LABELS: Record<string, string> = {
  setup: "Настройка",
  repair: "Ремонт",
  roster: "Контракты",
  construction: "Постройка"
};

export function BudgetHistoryPage() {
  const budget = useSeasonStore((state) => state.budget);
  const transactions = [...budget.transactions].reverse();

  return (
    <PageSurface>
      <PageHeader
        title="История бюджета"
        actions={
          <ButtonLink to={ROUTES.home} variant="secondary">
            На главную
          </ButtonLink>
        }
      />

      <section className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
        <StatBlock label="Начальный капитал" value={formatMoney(budget.startingMillions)} />
        <StatBlock label="Потрачено" value={formatMoney(budget.spentMillions)} />
        <StatBlock label="Доступно всего" value={formatMoney(budget.availableMillions)} />
        <StatBlock label="Фонд ремонта" value={formatMoney(budget.repairReserveMillions)} />
        <StatBlock label="Фонд настроек" value={formatMoney(budget.setupReserveMillions)} />
        <StatBlock
          label="Свободные деньги"
          value={formatMoney(budget.freeMillions)}
          accent="var(--color-primary)"
        />
      </section>

      <section className="mt-8 space-y-4">
        <SectionHeader title="Транзакции" />

        <div className="overflow-hidden border border-border bg-surface shadow-sm">
          <table className="w-full text-left font-mono text-sm">
            <thead className="bg-muted/50 text-[10px] font-black uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-4 py-3">Категория</th>
                <th className="px-4 py-3">Описание</th>
                <th className="px-4 py-3 text-right">Сумма</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {transactions.length > 0 ? (
                transactions.map((t) => (
                  <tr key={t.id} className="hover:bg-muted/30">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-foreground">
                          {CATEGORY_LABELS[t.category] || t.category}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">{t.label}</td>
                    <td className="px-4 py-3 text-right font-black text-danger">
                      -{formatMoney(t.amountMillions)}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={3} className="px-4 py-8 text-center text-muted-foreground">
                    Транзакций пока нет
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </PageSurface>
  );
}
