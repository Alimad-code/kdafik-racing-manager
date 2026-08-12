import { getDriver } from "@/features/season/lib/seasonViewData";

const FALLBACK_DRIVER_NAME = "Неизвестный пилот";

export function resolveLiveDriverName(driverId: string, fallbackName?: string) {
  const driver = getDriver(driverId);
  if (driver.code !== "---") {
    return `${driver.firstName} ${driver.lastName}`;
  }

  return fallbackName?.trim() || FALLBACK_DRIVER_NAME;
}
