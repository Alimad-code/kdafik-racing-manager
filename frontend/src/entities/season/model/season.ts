import { z } from "zod";

export const seasonStageStatusSchema = z.enum(["available", "locked", "completed"]);
export const sessionProgressStatusSchema = z.enum(["locked", "available", "completed"]);
export const practiceSegmentSchema = z.enum(["fp1", "fp2", "fp3"]);
export const practiceSegmentStatusSchema = z.enum(["locked", "available", "completed"]);
export const practiceCompletionStatusSchema = z.enum(["locked", "available", "completed"]);
export const weatherPrecipitationSchema = z.enum(["none", "light", "moderate", "heavy"]);
export const weatherSnapshotSchema = z.object({
  precipitation: weatherPrecipitationSchema,
  trackTemp: z.number(),
  rainIntensity: z.number().min(0).max(1),
  trackWetness: z.number().min(0).max(1)
});
export const raceForecastPointSchema = z.object({
  point: z.enum(["start", "one-third", "two-thirds", "finish"]),
  progress: z.number().min(0).max(1),
  confidence: z.string(),
  rainChance: z.number().min(0).max(1),
  expectedRain: weatherPrecipitationSchema,
  trackWetnessMin: z.number().min(0).max(1),
  trackWetnessMax: z.number().min(0).max(1),
  trackTemp: z.number(),
  temperatureMinC: z.number(),
  temperatureMaxC: z.number()
});
export const stageWeatherSchema = z.object({
  practice: z.object({
    fp1: weatherSnapshotSchema,
    fp2: weatherSnapshotSchema,
    fp3: weatherSnapshotSchema
  }),
  qualifying: weatherSnapshotSchema,
  raceForecast: z.array(raceForecastPointSchema).length(4)
});
export const tireCompoundSchema = z.enum(["Soft", "Medium", "Hard", "Intermediate", "Wet"]);
export const tireStrategyStintSchema = z.object({
  compound: tireCompoundSchema,
  startLap: z.number().int().positive(),
  endLap: z.number().int().positive(),
  pitWindowStartLap: z.number().int().positive().nullable().optional(),
  pitWindowEndLap: z.number().int().positive().nullable().optional()
});
export const tireStrategySchema = z.object({
  number: z.number().int().min(1).max(3),
  pitStopCount: z.number().int().min(1).max(3),
  stints: z.array(tireStrategyStintSchema).min(2).max(4)
});

export const practiceProgramSchema = z.object({
  stageId: z.string(),
  fp1Status: practiceSegmentStatusSchema,
  fp2Status: practiceSegmentStatusSchema,
  fp3Status: practiceSegmentStatusSchema,
  practiceCompletionStatus: practiceCompletionStatusSchema
});

export const stageSessionProgressSchema = z.object({
  stageId: z.string(),
  practiceStatus: sessionProgressStatusSchema,
  qualifyingStatus: sessionProgressStatusSchema,
  raceStatus: sessionProgressStatusSchema,
  practiceProgram: practiceProgramSchema.optional()
});

export const seasonSchema = z.object({
  id: z.string(),
  name: z.string(),
  year: z.number().int().positive(),
  selectedTeamId: z.string(),
  selectedDriverIds: z.array(z.string()).length(2),
  currentStageId: z.string(),
  stageIds: z.array(z.string()),
  stageProgress: z.array(stageSessionProgressSchema),
  status: z.enum(["setup", "in-progress", "completed"])
});

export const seasonStageSchema = z.object({
  id: z.string(),
  stageNumber: z.number().int().positive(),
  trackId: z.string(),
  status: seasonStageStatusSchema,
  weekendDate: z.string(),
  weather: stageWeatherSchema.nullable().optional(),
  tireStrategies: z.array(tireStrategySchema).length(3).nullable().optional(),
  recommendedStartingCompound: tireCompoundSchema.nullable().optional()
});

export type Season = z.infer<typeof seasonSchema>;
export type SeasonStageStatus = z.infer<typeof seasonStageStatusSchema>;
export type SessionProgressStatus = z.infer<typeof sessionProgressStatusSchema>;
export type PracticeSegment = z.infer<typeof practiceSegmentSchema>;
export type PracticeSegmentStatus = z.infer<typeof practiceSegmentStatusSchema>;
export type PracticeCompletionStatus = z.infer<typeof practiceCompletionStatusSchema>;
export type PracticeProgram = z.infer<typeof practiceProgramSchema>;
export type StageSessionProgress = z.infer<typeof stageSessionProgressSchema>;
export type SeasonStage = z.infer<typeof seasonStageSchema>;
export type WeatherPrecipitation = z.infer<typeof weatherPrecipitationSchema>;
export type WeatherSnapshot = z.infer<typeof weatherSnapshotSchema>;
export type RaceForecastPoint = z.infer<typeof raceForecastPointSchema>;
export type StageWeather = z.infer<typeof stageWeatherSchema>;
export type TireCompound = z.infer<typeof tireCompoundSchema>;
export type TireStrategyStint = z.infer<typeof tireStrategyStintSchema>;
export type TireStrategy = z.infer<typeof tireStrategySchema>;
