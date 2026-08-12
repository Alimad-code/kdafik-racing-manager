import { z } from "zod";

export const teamSchema = z.object({
  id: z.string(),
  name: z.string(),
  shortName: z.string(),
  baseCountry: z.string(),
  powerUnit: z.string(),
  color: z.string(),
  price: z.number().nonnegative(),
  carRating: z.number().int().min(1).max(100),
  reliability: z.number().int().min(1).max(100),
  setupCost: z.number().nonnegative(),
  repairCost: z.number().nonnegative(),
  carBuildCost: z.number().nonnegative(),
  minimumRepairReserve: z.number().nonnegative(),
  minimumSetupReserve: z.number().nonnegative(),
  minimumReserve: z.number().nonnegative()
});

export type Team = z.infer<typeof teamSchema>;
