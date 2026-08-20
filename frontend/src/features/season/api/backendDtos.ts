import type {
  BudgetSpendingCategory,
  CarCondition,
  SeasonStageStatus,
  SessionProgressStatus
} from "@/entities";

export type BackendErrorCode =
  | "INVALID_CREDENTIALS"
  | "EMAIL_ALREADY_REGISTERED"
  | "DISPLAY_NAME_ALREADY_REGISTERED"
  | "UNAUTHORIZED"
  | "INSUFFICIENT_FUNDS"
  | "INVALID_ROSTER"
  | "DUPLICATE_DRIVER"
  | "STAGE_LOCKED"
  | "SESSION_ALREADY_COMPLETED"
  | "PREVIOUS_SESSION_NOT_COMPLETED"
  | "SEASON_ALREADY_FINISHED"
  | "SEASON_NOT_IN_PROGRESS"
  | "ENTITY_NOT_FOUND"
  | "FORBIDDEN"
  | "INVALID_STATE_TRANSITION"
  | "VALIDATION_ERROR"
  | string;

export type BackendErrorResponse = {
  code: BackendErrorCode;
  message: string;
  details?: Record<string, unknown>;
};

export type AuthLoginRequestDto = {
  login: string;
  password: string;
};

export type AuthRegisterRequestDto = {
  displayName: string;
  email: string;
  password: string;
  legalAcceptances: LegalAcceptanceRequestDto[];
};

export type AcceptedResponseDto = { accepted: true };

export type EmailRequestDto = { email: string };

export type RegistrationChallengeDto = AcceptedResponseDto & {
  confirmationId: string;
  maskedEmail: string;
};

export type PasswordResetChallengeDto = AcceptedResponseDto & {
  resetId: string;
  maskedEmail: string;
};

export type RegistrationResendRequestDto = {
  confirmationId: string;
};

export type RegistrationConfirmationRequestDto = RegistrationResendRequestDto & {
  code: string;
  legalAcceptances?: LegalAcceptanceRequestDto[];
};

export type PasswordResetResendRequestDto = {
  resetId: string;
};

export type ResetPasswordRequestDto = PasswordResetResendRequestDto & {
  code: string;
  newPassword: string;
};

export type LegalDocumentKind = "privacy_policy" | "personal_data_consent" | "user_agreement";
export type PublicLegalDocumentKind = LegalDocumentKind | "cookie_storage_notice";

export type LegalDocumentReadDto = {
  kind: LegalDocumentKind;
  version: string;
  title: string;
  publicPath: string;
  contentSha256: string;
  effectiveAt: string;
  requiredAtRegistration: boolean;
};

export type LegalDocumentContentReadDto = {
  kind: PublicLegalDocumentKind;
  version: string;
  title: string;
  publicPath: string;
  contentSha256: string;
  effectiveAt: string;
  isDraft: boolean;
  content: string;
};

export type LegalAcceptanceRequestDto = {
  kind: LegalDocumentKind;
  version: string;
  accepted: boolean;
};

export type LegalAcceptanceStatusReadDto = {
  document: LegalDocumentReadDto;
  accepted: boolean;
};

export type DriverReadDto = {
  id: string;
  number: number;
  firstName: string;
  lastName: string;
  code: string;
  nationality: string;
  priceMillions: number;
  pace: number;
  stability: number;
};

export type TeamReadDto = {
  id: string;
  name: string;
  shortName: string;
  baseCountry: string;
  powerUnit: string;
  color?: string | null;
  priceMillions: number;
  carRating: number;
  reliability: number;
  setupCostMillions: number;
  repairCostMillions: number;
  carBuildCostMillions: number;
  minimumRepairReserveMillions: number;
  minimumSetupReserveMillions: number;
  minimumReserveMillions: number;
};

export type TrackReadDto = {
  id: string;
  name: string;
  country: string;
  profile: "speed" | "balanced" | "technical";
  laps: number;
  lengthKm: number;
  climate: {
    rainProbability: number;
    trackTemperatureMinC: number;
    trackTemperatureMaxC: number;
    variability: number;
  };
  svgPath: string;
};

export type CalendarStageReadDto = {
  stageNumber: number;
  trackId: string;
  weekendDate: string;
};

export type CatalogReadDto = {
  drivers: DriverReadDto[];
  teams: TeamReadDto[];
  tracks: TrackReadDto[];
  calendar: CalendarStageReadDto[];
};

export type BudgetStateReadDto = {
  startingBudgetMillions: number;
  spentBudgetMillions: number;
  availableBudgetMillions: number;
  repairReserveMillions: number;
  setupReserveMillions: number;
  freeBudgetMillions: number;
};

export type BudgetTransactionReadDto = {
  id: string;
  category: BudgetSpendingCategory;
  label: string;
  amountMillions: number;
  balanceBeforeMillions: number;
  balanceAfterMillions: number;
  referenceType: string | null;
  referenceId: string | null;
  createdAt: string;
};

export type CarReadDto = {
  id: string;
  teamId: string;
  driverId: string;
  speed: number;
  reliability: number;
  condition: CarCondition;
  wingsSetting?: number;
  suspensionSetting?: number;
  gearboxSetting?: number;
};

export type SessionTypeDto = "practice" | "qualifying" | "race";
export type PracticeSegmentDto = "fp1" | "fp2" | "fp3";
export type PracticeSegmentStatusDto = "locked" | "available" | "completed";
export type PracticeCompletionStatusDto = "locked" | "available" | "completed";

export type PracticeProgramReadDto = {
  stageId: string;
  fp1Status: PracticeSegmentStatusDto;
  fp2Status: PracticeSegmentStatusDto;
  fp3Status: PracticeSegmentStatusDto;
  practiceCompletionStatus: PracticeCompletionStatusDto;
};

export type SeasonStageReadDto = {
  id: string;
  trackId: string;
  stageNumber: number;
  weekendDate: string;
  status: SeasonStageStatus;
  practiceStatus: SessionProgressStatus;
  qualifyingStatus: SessionProgressStatus;
  raceStatus: SessionProgressStatus;
  practiceProgram?: PracticeProgramReadDto | null;
  latestCompletedSession?: SessionTypeDto | null;
  track?: TrackReadDto | null;
  weather?: StageWeatherReadDto | null;
  tireStrategies?: TireStrategyReadDto[] | null;
  recommendedStartingCompound?: TireStrategyStintReadDto["compound"] | null;
};

export type TireStrategyStintReadDto = {
  compound: "Soft" | "Medium" | "Hard" | "Intermediate" | "Wet";
  startLap: number;
  endLap: number;
  pitWindowStartLap?: number | null;
  pitWindowEndLap?: number | null;
};

export type TireStrategyReadDto = {
  number: number;
  pitStopCount: number;
  stints: TireStrategyStintReadDto[];
};

export type WeatherSnapshotReadDto = {
  precipitation: "none" | "light" | "moderate" | "heavy";
  trackTemp: number;
  rainIntensity: number;
  trackWetness: number;
};

export type RaceForecastPointReadDto = {
  point: "start" | "one-third" | "two-thirds" | "finish";
  progress: number;
  confidence: string;
  rainChance: number;
  expectedRain: "none" | "light" | "moderate" | "heavy";
  trackWetnessMin: number;
  trackWetnessMax: number;
  trackTemp: number;
  temperatureMinC: number;
  temperatureMaxC: number;
};

export type StageWeatherReadDto = {
  practice: Record<PracticeSegmentDto, WeatherSnapshotReadDto>;
  qualifying: WeatherSnapshotReadDto;
  raceForecast: RaceForecastPointReadDto[];
};

export type UserReadDto = {
  id: string;
  displayName: string;
  email: string | null;
  role: "team-principal" | "race-engineer" | "viewer";
  activeSeasonId: string | null;
};

export type ProfileReadDto = UserReadDto & {
  createdAt: string;
  updatedAt: string;
};

export type UpdateMeRequestDto = {
  displayName: string;
};

export type ChangePasswordRequestDto = {
  currentPassword: string;
  newPassword: string;
};

export type DeleteAccountRequestDto = {
  currentPassword: string;
};

export type SeasonReadDto = {
  id: string;
  userId: string;
  name: string;
  year: number;
  status: "setup" | "in-progress" | "completed";
  selectedTeamId: string | null;
  currentStageId: string | null;
  currentStage: SeasonStageReadDto | null;
  budget: BudgetStateReadDto;
  selectedDrivers: DriverReadDto[];
  selectedTeam: TeamReadDto | null;
  cars: CarReadDto[];
  stages: SeasonStageReadDto[];
  budgetTransactions: BudgetTransactionReadDto[];
};

export type SessionReadDto = {
  user: UserReadDto;
  activeSeasonId: string | null;
  activeSeason: SeasonReadDto | null;
};

export type AuthResponseDto = {
  accessToken: string;
  tokenType: "bearer";
  expiresInSeconds: number;
  user: UserReadDto;
  activeSeasonId: string | null;
  activeSeason: SeasonReadDto | null;
};

export type ResultStatusDto = "classified" | "no-time" | "dnf" | "dns" | "disqualified";
export type RaceEventTypeDto =
  | "clean-race"
  | "driver-mistake"
  | "damage"
  | "dnf"
  | "no-time"
  | "technical-issue";

export type CarSetupReadDto = {
  id: string;
  seasonId: string;
  stageId: string;
  carId: string;
  wingsSetting: number;
  suspensionSetting: number;
  gearboxSetting: number;
  setupBand: "low" | "medium" | "high";
  costMillions: number;
  appliesToSession: SessionTypeDto;
  createdAt: string;
};

export type SessionResultReadDto = {
  id: string;
  seasonId: string;
  stageId: string;
  driverId: string;
  teamId: string;
  carId: string;
  position: number;
  bestLap: string | null;
  gap: string;
  laps: number;
  points: number;
  status: ResultStatusDto;
  event: RaceEventTypeDto | null;
  reason: string | null;
};

export type PracticeResultReadDto = SessionResultReadDto & {
  practiceSegment?: PracticeSegmentDto | null;
  setupFeedback: string | null;
  engineerRecommendation: string | null;
};

export type QualifyingResultReadDto = SessionResultReadDto;

export type RaceResultReadDto = Omit<SessionResultReadDto, "position"> & {
  gridPosition: number;
  finishPosition: number;
  bestLapNumber?: number | null;
  maxSpeedKph?: number | null;
};

export type DriverStandingReadDto = {
  id: string;
  seasonId: string;
  driverId: string;
  teamId: string;
  position: number;
  points: number;
  wins: number;
  podiums: number;
};

export type ConstructorStandingReadDto = {
  id: string;
  seasonId: string;
  teamId: string;
  position: number;
  points: number;
  wins: number;
  podiums: number;
};

export type StandingsReadDto = {
  driverStandings: DriverStandingReadDto[];
  constructorStandings: ConstructorStandingReadDto[];
  selectedTeamRank: number | null;
};

export type CarSetupSaveResponseDto = {
  season: SeasonReadDto;
  stage: SeasonStageReadDto;
  setups: CarSetupReadDto[];
};

export type PracticeRunResponseDto = {
  season: SeasonReadDto;
  stage: SeasonStageReadDto;
  practiceProgram?: PracticeProgramReadDto | null;
  practiceResults: PracticeResultReadDto[];
};

export type PracticeProgramResponseDto = {
  season: SeasonReadDto;
  stage: SeasonStageReadDto;
  practiceProgram: PracticeProgramReadDto;
  practiceResults: PracticeResultReadDto[];
};

export type QualifyingRunResponseDto = {
  season: SeasonReadDto;
  stage: SeasonStageReadDto;
  qualifyingResults: QualifyingResultReadDto[];
};

export type RaceResultsResponseDto = {
  season: SeasonReadDto;
  stage: SeasonStageReadDto;
  raceResults: RaceResultReadDto[];
  events: unknown[];
  standings: StandingsReadDto;
};

export type RepairCarResponseDto = {
  season: SeasonReadDto;
  car: CarReadDto;
  transaction: BudgetTransactionReadDto;
};
