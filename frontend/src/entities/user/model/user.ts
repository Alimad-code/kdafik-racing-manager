import { z } from "zod";

export const userSchema = z.object({
  id: z.string(),
  displayName: z.string(),
  email: z.string().nullable().optional(),
  role: z.enum(["team-principal", "race-engineer", "viewer"]),
  selectedTeamId: z.string().nullable(),
  activeSeasonId: z.string().nullable()
});

export type User = z.infer<typeof userSchema>;
