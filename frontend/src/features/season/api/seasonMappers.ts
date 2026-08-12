import type {
  BudgetState,
  BudgetTransaction,
  Car,
  ChampionshipStanding,
  ConstructorStanding,
  Driver,
  PracticeProgram,
  PracticeResult,
  QualifyingResult,
  RaceResult,
  Season,
  SeasonStage,
  StageSessionProgress,
  Team,
  Track,
  User
} from "@/entities";
import type {
  BudgetStateReadDto,
  BudgetTransactionReadDto,
  CarReadDto,
  ConstructorStandingReadDto,
  DriverReadDto,
  PracticeResultReadDto,
  QualifyingResultReadDto,
  RaceResultReadDto,
  SeasonReadDto,
  SeasonStageReadDto,
  TeamReadDto,
  TrackReadDto,
  UserReadDto
} from "@/features/season/api/backendDtos";

export function mapDriver(dto: DriverReadDto): Driver {
  return {
    id: dto.id,
    number: dto.number,
    firstName: dto.firstName,
    lastName: dto.lastName,
    code: dto.code,
    nationality: dto.nationality,
    price: dto.priceMillions,
    pace: dto.pace,
    stability: dto.stability
  };
}

export function mapTeam(dto: TeamReadDto): Team {
  return {
    id: dto.id,
    name: dto.name,
    shortName: dto.shortName,
    baseCountry: dto.baseCountry,
    powerUnit: dto.powerUnit,
    color: dto.color ?? "#64748b",
    price: dto.priceMillions,
    carRating: dto.carRating,
    reliability: dto.reliability,
    setupCost: dto.setupCostMillions,
    repairCost: dto.repairCostMillions,
    carBuildCost: dto.carBuildCostMillions,
    minimumRepairReserve: dto.minimumRepairReserveMillions,
    minimumSetupReserve: dto.minimumSetupReserveMillions,
    minimumReserve: dto.minimumReserveMillions
  };
}

export function mapTrack(dto: TrackReadDto): Track {
  return {
    id: dto.id,
    name: dto.name,
    country: dto.country,
    profile: dto.profile,
    laps: dto.laps,
    lengthKm: dto.lengthKm,
    climate: dto.climate,
    svgPath: dto.svgPath
  };
}

export function mapStage(dto: SeasonStageReadDto): SeasonStage {
  return {
    id: dto.id,
    stageNumber: dto.stageNumber,
    trackId: dto.trackId,
    status: dto.status,
    weekendDate: dto.weekendDate,
    weather: dto.weather ?? null,
    tireStrategies: dto.tireStrategies ?? null,
    recommendedStartingCompound: dto.recommendedStartingCompound ?? null
  };
}

function derivePracticeProgram(dto: SeasonStageReadDto): PracticeProgram {
  if (dto.practiceProgram) {
    return dto.practiceProgram;
  }

  const status = dto.practiceStatus;

  if (status === "completed") {
    return {
      stageId: dto.id,
      fp1Status: "completed",
      fp2Status: "completed",
      fp3Status: "completed",
      practiceCompletionStatus: "completed"
    };
  }

  if (status === "available") {
    return {
      stageId: dto.id,
      fp1Status: "available",
      fp2Status: "locked",
      fp3Status: "locked",
      practiceCompletionStatus: "locked"
    };
  }

  return {
    stageId: dto.id,
    fp1Status: "locked",
    fp2Status: "locked",
    fp3Status: "locked",
    practiceCompletionStatus: "locked"
  };
}

export function mapStageProgress(dto: SeasonStageReadDto): StageSessionProgress {
  return {
    stageId: dto.id,
    practiceStatus: dto.practiceStatus,
    qualifyingStatus: dto.qualifyingStatus,
    raceStatus: dto.raceStatus,
    practiceProgram: derivePracticeProgram(dto)
  };
}

export function mapCar(dto: CarReadDto): Car {
  return {
    id: dto.id,
    driverId: dto.driverId,
    speed: dto.speed,
    reliability: dto.reliability,
    condition: dto.condition,
    wingsSetting: dto.wingsSetting ?? 50,
    suspensionSetting: dto.suspensionSetting ?? 50,
    gearboxSetting: dto.gearboxSetting ?? 50
  };
}

function mapBudgetTransaction(dto: BudgetTransactionReadDto): BudgetTransaction {
  return {
    id: dto.id,
    category: dto.category,
    label: dto.label,
    amountMillions: dto.amountMillions
  };
}

export function mapBudget(
  dto: BudgetStateReadDto,
  transactions: BudgetTransactionReadDto[]
): BudgetState {
  return {
    startingMillions: dto.startingBudgetMillions,
    spentMillions: dto.spentBudgetMillions,
    availableMillions: dto.availableBudgetMillions,
    repairReserveMillions: dto.repairReserveMillions,
    setupReserveMillions: dto.setupReserveMillions,
    freeMillions: dto.freeBudgetMillions,
    transactions: transactions.map(mapBudgetTransaction)
  };
}

export function mapSeason(dto: SeasonReadDto): Season {
  const stageIds = dto.stages.map((stage) => stage.id);

  return {
    id: dto.id,
    name: dto.name,
    year: dto.year,
    selectedTeamId: dto.selectedTeamId ?? "",
    selectedDriverIds: dto.selectedDrivers.map((driver) => driver.id),
    currentStageId: dto.currentStageId ?? stageIds[0] ?? "",
    stageIds,
    stageProgress: dto.stages.map(mapStageProgress),
    status: dto.status
  };
}

export function mapUser(dto: UserReadDto): User {
  return {
    id: dto.id,
    displayName: dto.displayName,
    email: dto.email,
    role: dto.role,
    selectedTeamId: null,
    activeSeasonId: dto.activeSeasonId
  };
}

function mapResultStatus(status: PracticeResultReadDto["status"]) {
  return status === "dnf" || status === "dns" ? "retired" : status;
}

function mapSessionEvent(event: PracticeResultReadDto["event"]) {
  if (event === "clean-race") {
    return "clean-race" as const;
  }

  return event ?? undefined;
}

export function mapPracticeResult(dto: PracticeResultReadDto): PracticeResult {
  return {
    id: dto.id,
    sessionType: "practice",
    stageId: dto.stageId,
    position: dto.position,
    driverId: dto.driverId,
    teamId: dto.teamId,
    bestLap: dto.bestLap || undefined,
    gap: dto.gap,
    laps: dto.laps,
    points: dto.points,
    status: mapResultStatus(dto.status),
    event: mapSessionEvent(dto.event),
    reason: dto.engineerRecommendation ?? dto.setupFeedback ?? dto.reason ?? undefined,
    practiceSegment: dto.practiceSegment ?? "fp1",
    setupFeedback: dto.setupFeedback ?? undefined,
    engineerRecommendation: dto.engineerRecommendation ?? undefined
  };
}

export function mapQualifyingResult(dto: QualifyingResultReadDto): QualifyingResult {
  return {
    id: dto.id,
    sessionType: "qualifying",
    stageId: dto.stageId,
    position: dto.position,
    driverId: dto.driverId,
    teamId: dto.teamId,
    bestLap: dto.bestLap || undefined,
    gap: dto.gap,
    laps: dto.laps,
    points: dto.points,
    status: mapResultStatus(dto.status),
    event: mapSessionEvent(dto.event),
    reason: dto.reason ?? undefined
  };
}

export function mapRaceResult(dto: RaceResultReadDto): RaceResult {
  return {
    id: dto.id,
    sessionType: "race",
    stageId: dto.stageId,
    position: dto.finishPosition,
    gridPosition: dto.gridPosition,
    driverId: dto.driverId,
    teamId: dto.teamId,
    bestLap: dto.bestLap || undefined,
    bestLapNumber: dto.bestLapNumber ?? undefined,
    maxSpeedKph: dto.maxSpeedKph ?? undefined,
    gap: dto.gap,
    laps: dto.laps,
    points: dto.points,
    status: mapResultStatus(dto.status),
    event: mapSessionEvent(dto.event),
    reason: dto.reason ?? undefined
  };
}

export function mapDriverStanding(dto: {
  driverId: string;
  teamId: string;
  position: number;
  points: number;
  wins: number;
  podiums: number;
}): ChampionshipStanding {
  return {
    driverId: dto.driverId,
    teamId: dto.teamId,
    position: dto.position,
    points: dto.points,
    wins: dto.wins,
    podiums: dto.podiums
  };
}

export function mapConstructorStanding(dto: ConstructorStandingReadDto): ConstructorStanding {
  return {
    teamId: dto.teamId,
    position: dto.position,
    points: dto.points,
    wins: dto.wins,
    podiums: dto.podiums
  };
}
