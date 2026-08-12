import type { QualifyingResult, TireCompound } from "@/entities";

export type GridRow = QualifyingResult & {
  compound?: TireCompound;
};
