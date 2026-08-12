import { z } from "zod";

export const driverSchema = z.object({
  id: z.string(),
  number: z.number().int().positive(),
  firstName: z.string(),
  lastName: z.string(),
  code: z.string().length(3),
  nationality: z.string(),
  price: z.number().nonnegative(),
  pace: z.number().int().min(1).max(100),
  stability: z.number().int().min(1).max(100)
});

export type Driver = z.infer<typeof driverSchema>;
