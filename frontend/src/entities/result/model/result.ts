import { z } from "zod";
import { practiceSegmentSchema } from "@/entities/season/model/season";

export const sessionTypeSchema = z.enum(["practice", "qualifying", "race"]);
export const sessionEventSchema = z.enum([
  "clean-run",
  "setup-mismatch",
  "no-time",
  "clean-race",
  "driver-mistake",
  "damage",
  "dnf",
  "technical-issue"
]);

export const sessionResultSchema = z.object({
  id: z.string(),
  sessionType: sessionTypeSchema,
  stageId: z.string(),
  position: z.number().int().positive(),
  driverId: z.string(),
  teamId: z.string(),
  bestLap: z.string().optional(),
  gap: z.string(),
  laps: z.number().int().nonnegative(),
  points: z.number().int().nonnegative(),
  status: z.enum(["classified", "retired", "no-time", "disqualified"]),
  event: sessionEventSchema.optional(),
  reason: z.string().optional()
});

export const practiceResultSchema = sessionResultSchema.extend({
  sessionType: z.literal("practice"),
  practiceSegment: practiceSegmentSchema.optional(),
  setupFeedback: z.string().optional(),
  engineerRecommendation: z.string().optional()
});

export const qualifyingResultSchema = sessionResultSchema.extend({
  sessionType: z.literal("qualifying")
});

export const raceResultSchema = sessionResultSchema.extend({
  sessionType: z.literal("race"),
  gridPosition: z.number().int().positive().optional(),
  bestLapNumber: z.number().int().positive().optional(),
  maxSpeedKph: z.number().nonnegative().optional()
});

export const championshipStandingSchema = z.object({
  position: z.number().int().positive(),
  driverId: z.string(),
  teamId: z.string(),
  points: z.number().int().nonnegative(),
  wins: z.number().int().nonnegative(),
  podiums: z.number().int().nonnegative()
});

export const constructorStandingSchema = z.object({
  position: z.number().int().positive(),
  teamId: z.string(),
  points: z.number().int().nonnegative(),
  wins: z.number().int().nonnegative(),
  podiums: z.number().int().nonnegative()
});

export type SessionType = z.infer<typeof sessionTypeSchema>;
export type SessionEvent = z.infer<typeof sessionEventSchema>;
export type SessionResult = z.infer<typeof sessionResultSchema>;
export type PracticeResult = z.infer<typeof practiceResultSchema>;
export type QualifyingResult = z.infer<typeof qualifyingResultSchema>;
export type RaceResult = z.infer<typeof raceResultSchema>;
export type ChampionshipStanding = z.infer<typeof championshipStandingSchema>;
export type ConstructorStanding = z.infer<typeof constructorStandingSchema>;
