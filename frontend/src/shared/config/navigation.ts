import { ROUTES } from "@/shared/constants/routes";
import type { AppNavigationItem } from "@/shared/types/navigation";

export const appNavigation: AppNavigationItem[] = [
  {
    code: "01",
    detail: "Сводка штаба",
    label: "Главная панель",
    to: ROUTES.home
  },
  {
    code: "02",
    detail: "Команда и бюджет",
    label: "Настройка состава",
    to: ROUTES.seasonSetup
  },
  {
    code: "03",
    detail: "Этапы и следующий шаг",
    label: "Календарь сезона",
    to: ROUTES.seasonOverview
  },
  {
    code: "04",
    detail: "Личный и командный зачет",
    label: "Зачеты чемпионата",
    to: ROUTES.championshipSummary
  }
];
