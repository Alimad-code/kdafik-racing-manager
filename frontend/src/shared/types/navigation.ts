import type { AppRoute } from "@/shared/constants/routes";

export type AppNavigationItem = {
  code: string;
  detail: string;
  label: string;
  to: AppRoute;
};
