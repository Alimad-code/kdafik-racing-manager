import { z } from "zod";

export const trackProfileSchema = z.enum(["speed", "balanced", "technical"]);

export const trackSchema = z
  .object({
    id: z.string(),
    name: z.string(),
    country: z.string(),
    profile: trackProfileSchema,
    laps: z.number().int().positive(),
    lengthKm: z.number().positive(),
    climate: z
      .object({
        rainProbability: z.number().min(0).max(1),
        trackTemperatureMinC: z.number(),
        trackTemperatureMaxC: z.number(),
        variability: z.number().min(0).max(1)
      })
      .strict(),
    svgPath: z.string()
  })
  .strict();

export type Track = z.infer<typeof trackSchema>;
export type TrackProfile = z.infer<typeof trackProfileSchema>;
