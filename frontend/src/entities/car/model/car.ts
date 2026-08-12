import { z } from "zod";

export const carConditionSchema = z.enum(["healthy", "damaged", "heavily-damaged"]);

export const carSchema = z.object({
  id: z.string(),
  driverId: z.string(),
  speed: z.number().int().min(1).max(100),
  reliability: z.number().int().min(1).max(100),
  condition: carConditionSchema,
  wingsSetting: z.number().int().min(0).max(100),
  suspensionSetting: z.number().int().min(0).max(100),
  gearboxSetting: z.number().int().min(0).max(100)
});

export type CarCondition = z.infer<typeof carConditionSchema>;
export type Car = z.infer<typeof carSchema>;
