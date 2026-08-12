import type {
  Car,
  ChampionshipStanding,
  ConstructorStanding,
  Driver,
  PracticeProgram,
  PracticeSegment,
  PracticeResult,
  QualifyingResult,
  RaceResult,
  Season,
  SeasonStage,
  SessionType,
  Team,
  Track,
  User
} from "@/entities";
import { ApiError, apiRequest } from "@/features/season/api/apiClient";
import type {
  AuthResponseDto,
  CarSetupSaveResponseDto,
  CatalogReadDto,
  PracticeRunResponseDto,
  PracticeProgramResponseDto,
  QualifyingRunResponseDto,
  RaceResultsResponseDto,
  RepairCarResponseDto,
  SeasonReadDto,
  SessionReadDto,
  StandingsReadDto
} from "@/features/season/api/backendDtos";
import type { SeasonRepository } from "@/features/season/api/seasonRepository";
import {
  mapBudget,
  mapCar,
  mapConstructorStanding,
  mapDriver,
  mapDriverStanding,
  mapPracticeResult,
  mapQualifyingResult,
  mapRaceResult,
  mapSeason,
  mapStage,
  mapTeam,
  mapTrack,
  mapUser
} from "@/features/season/api/seasonMappers";

type Cache = {
  currentUser: User;
  activeSeason: Season | null;
  drivers: Driver[];
  teams: Team[];
  tracks: Track[];
  stages: SeasonStage[];
  cars: Car[];
  budget: ReturnType<typeof mapBudget> | null;
  practicePrograms: Record<string, PracticeProgram>;
  practiceResults: PracticeResult[];
  qualifyingResults: QualifyingResult[];
  raceResults: RaceResult[];
  standings: ChampionshipStanding[];
  constructorStandings: ConstructorStanding[];
  lastError: ApiError | null;
};

const emptyUser: User = {
  id: "",
  displayName: "",
  role: "team-principal",
  selectedTeamId: null,
  activeSeasonId: null
};

function createEmptyCache(): Cache {
  return {
    currentUser: emptyUser,
    activeSeason: null,
    drivers: [],
    teams: [],
    tracks: [],
    stages: [],
    cars: [],
    budget: null,
    practicePrograms: {},
    practiceResults: [],
    qualifyingResults: [],
    raceResults: [],
    standings: [],
    constructorStandings: [],
    lastError: null
  };
}

function sortByPosition<T extends { position: number }>(rows: T[]) {
  return [...rows].sort((left, right) => left.position - right.position);
}

const practiceSegmentOrder: Record<PracticeSegment, number> = {
  fp1: 1,
  fp2: 2,
  fp3: 3
};

function sortPracticeResults(rows: PracticeResult[]) {
  return [...rows].sort((left, right) => {
    const segmentDelta =
      practiceSegmentOrder[left.practiceSegment ?? "fp1"] -
      practiceSegmentOrder[right.practiceSegment ?? "fp1"];

    return segmentDelta || left.position - right.position;
  });
}

class BackendSeasonRepository implements SeasonRepository {
  private cache: Cache = createEmptyCache();

  getCurrentUser = () => this.cache.currentUser;

  updateCurrentUser = (user: User) => {
    this.cache.currentUser = user;
  };
  getActiveSeason = () => this.cache.activeSeason;
  getDrivers = () => this.cache.drivers;
  getTeams = () => this.cache.teams;
  getTracks = () => this.cache.tracks;
  getStages = () => this.cache.stages;
  getCars = () => this.cache.cars;
  getBudget = () =>
    this.cache.budget ?? {
      startingMillions: 0,
      spentMillions: 0,
      availableMillions: 0,
      repairReserveMillions: 0,
      setupReserveMillions: 0,
      freeMillions: 0,
      transactions: []
    };
  getPracticeResults = () => this.cache.practiceResults;
  getPracticeResultsByStage = (stageId: string) =>
    this.cache.practiceResults.filter((result) => result.stageId === stageId);
  getPracticeProgramByStage = (stageId: string) =>
    this.cache.practicePrograms[stageId] ??
    this.cache.activeSeason?.stageProgress.find((progress) => progress.stageId === stageId)
      ?.practiceProgram ??
    null;
  getQualifyingResults = () => this.cache.qualifyingResults;
  getQualifyingResultsByStage = (stageId: string) =>
    this.cache.qualifyingResults.filter((result) => result.stageId === stageId);
  getRaceResults = () => this.cache.raceResults;
  getRaceResultsByStage = (stageId: string) =>
    this.cache.raceResults.filter((result) => result.stageId === stageId);
  getChampionshipStandings = () => this.cache.standings;
  getConstructorStandings = () => this.cache.constructorStandings;
  getLastError = () => this.cache.lastError;
  clearLastError = () => {
    this.cache.lastError = null;
  };

  syncAuthSession = (authSession: AuthResponseDto) => {
    this.cache.currentUser = mapUser(authSession.user);

    if (authSession.activeSeason) {
      this.applySeason(authSession.activeSeason);
      return;
    }

    this.cache.activeSeason = null;
    this.cache.currentUser = {
      ...this.cache.currentUser,
      activeSeasonId: authSession.activeSeasonId
    };
  };

  clearSession = () => {
    this.cache = createEmptyCache();
  };

  async bootstrap() {
    await this.withErrorBoundary(async () => {
      const [catalog, session] = await Promise.all([
        apiRequest<CatalogReadDto>("/catalog"),
        apiRequest<SessionReadDto>("/session")
      ]);

      this.applyCatalog(catalog);
      this.cache.currentUser = mapUser(session.user);

      if (session.activeSeason) {
        this.applySeason(session.activeSeason);
        await this.loadStandings().catch((error: unknown) => {
          if (!(error instanceof ApiError && error.code === "ENTITY_NOT_FOUND")) {
            throw error;
          }
        });
      }
    });
  }

  async createSeason() {
    return this.withErrorBoundary(async () => {
      const season = await apiRequest<SeasonReadDto>("/seasons", {
        method: "POST",
        body: JSON.stringify({ name: "MVP Season", year: 2026 })
      });
      this.applySeason(season);
      return mapSeason(season);
    });
  }

  async refreshSeason() {
    const seasonId = this.requireSeasonId(false);

    if (!seasonId) {
      return null;
    }

    return this.withErrorBoundary(async () => {
      const season = await apiRequest<SeasonReadDto>(`/seasons/${seasonId}`);
      this.applySeason(season);
      return mapSeason(season);
    });
  }

  async startNewSeason() {
    return this.withErrorBoundary(async () => {
      const seasonId = this.requireSeasonId(true);
      const season = await apiRequest<SeasonReadDto>(`/seasons/${seasonId}/restart`, {
        method: "POST"
      });
      this.clearSeasonProtocolCache();
      this.applySeason(season);
      return mapSeason(season);
    });
  }

  async confirmRoster(driverIds: string[], teamId: string) {
    return this.withErrorBoundary(async () => {
      const seasonId = this.requireSeasonId(true);
      const season = await apiRequest<SeasonReadDto>(`/seasons/${seasonId}/roster`, {
        method: "POST",
        body: JSON.stringify({ driverIds, teamId })
      });
      this.applySeason(season);
      return mapSeason(season);
    });
  }

  async saveCarSetups(
    session: SessionType,
    setups?: Array<{
      carId: string;
      wingsSetting: number;
      suspensionSetting: number;
      gearboxSetting: number;
    }>,
    stageIdOverride?: string
  ) {
    return this.withErrorBoundary(async () => {
      const seasonId = this.requireSeasonId(true);
      const stageId = stageIdOverride ?? this.requireStageId();

      const setupPayloads =
        setups ??
        this.cache.cars.map((car) => ({
          carId: car.id,
          wingsSetting: car.wingsSetting,
          suspensionSetting: car.suspensionSetting,
          gearboxSetting: car.gearboxSetting
        }));

      const response = await apiRequest<CarSetupSaveResponseDto>(
        `/seasons/${seasonId}/stages/${stageId}/car-setups`,
        {
          method: "POST",
          body: JSON.stringify({
            appliesToSession: session,
            setups: setupPayloads.map((s) => ({
              carId: s.carId,
              wingsSetting: s.wingsSetting,
              suspensionSetting: s.suspensionSetting,
              gearboxSetting: s.gearboxSetting
            }))
          })
        }
      );
      this.applySeason(response.season);
      return mapSeason(response.season);
    });
  }

  async readCarSetups(session: SessionType) {
    return this.withErrorBoundary(async () => {
      const seasonId = this.requireSeasonId(true);
      const stageId = this.requireStageId();
      const response = await apiRequest<CarSetupSaveResponseDto>(
        `/seasons/${seasonId}/stages/${stageId}/car-setups?appliesToSession=${session}`
      );
      this.applySeason(response.season);
      return mapSeason(response.season);
    });
  }

  async runPracticeSegment(segment: PracticeSegment) {
    return this.withErrorBoundary(async () => {
      const seasonId = this.requireSeasonId(true);
      const stageId = this.requireStageId();
      const response = await apiRequest<PracticeRunResponseDto>(
        `/seasons/${seasonId}/stages/${stageId}/practice/${segment}/run`,
        { method: "POST" }
      );
      this.applySeason(response.season);
      this.applyPracticeProgram(response);
      return this.cache.practiceResults;
    });
  }

  async completePractice() {
    return this.withErrorBoundary(async () => {
      const seasonId = this.requireSeasonId(true);
      const stageId = this.requireStageId();
      const response = await apiRequest<PracticeProgramResponseDto>(
        `/seasons/${seasonId}/stages/${stageId}/practice/complete`,
        { method: "POST" }
      );
      this.applySeason(response.season);
      this.applyPracticeProgram(response);
      return response.practiceProgram;
    });
  }

  async readPracticeProgram() {
    return this.withErrorBoundary(async () => {
      const response = await this.readSessionResultsOrEmpty<PracticeRunResponseDto>("practice");
      if (!response) {
        this.cache.practiceResults = [];
        return this.cache.practiceResults;
      }

      this.applySeason(response.season);
      this.applyPracticeProgram(response);
      return this.cache.practiceResults;
    });
  }

  async runQualifying() {
    return this.withErrorBoundary(async () => {
      const response = await this.runSession<QualifyingRunResponseDto>("qualifying");
      this.applySeason(response.season);
      this.cache.qualifyingResults = sortByPosition(
        response.qualifyingResults.map(mapQualifyingResult)
      );
      return this.cache.qualifyingResults;
    });
  }

  async readQualifyingResults() {
    return this.withErrorBoundary(async () => {
      const response = await this.readSessionResultsOrEmpty<QualifyingRunResponseDto>("qualifying");

      if (!response) {
        this.cache.qualifyingResults = [];
        return this.cache.qualifyingResults;
      }

      this.applySeason(response.season);
      this.cache.qualifyingResults = sortByPosition(
        response.qualifyingResults.map(mapQualifyingResult)
      );
      return this.cache.qualifyingResults;
    });
  }

  async readRaceResults(stageId?: string, options: { waitForAutosave?: boolean } = {}) {
    return this.withErrorBoundary(async () => {
      const targetStageId = stageId ?? this.requireStageId();
      const attempts = options.waitForAutosave ? 8 : 1;
      let response: RaceResultsResponseDto | null = null;

      for (let attempt = 1; attempt <= attempts; attempt += 1) {
        try {
          response = await this.readSessionResults<RaceResultsResponseDto>("race", targetStageId);
          break;
        } catch (error) {
          if (
            !(error instanceof ApiError) ||
            error.code !== "ENTITY_NOT_FOUND" ||
            attempt === attempts
          ) {
            if (error instanceof ApiError && error.code === "ENTITY_NOT_FOUND") break;
            throw error;
          }

          await new Promise((resolve) => window.setTimeout(resolve, 500));
        }
      }

      if (!response) {
        this.cache.raceResults = this.cache.raceResults.filter(
          (result) => result.stageId !== targetStageId
        );
        return this.cache.raceResults;
      }

      this.applySeason(response.season);
      this.replaceRaceResultsForStage(
        response.stage.id ?? targetStageId,
        response.raceResults.map(mapRaceResult)
      );
      this.cache.standings = response.standings.driverStandings.map(mapDriverStanding);
      this.cache.constructorStandings =
        response.standings.constructorStandings.map(mapConstructorStanding);
      return this.cache.raceResults;
    });
  }

  async repairCar(carId: string) {
    return this.withErrorBoundary(async () => {
      const seasonId = this.requireSeasonId(true);
      const response = await apiRequest<RepairCarResponseDto>(
        `/seasons/${seasonId}/cars/${carId}/repair`,
        {
          method: "POST"
        }
      );
      this.applySeason(response.season);
      return mapCar(response.car);
    });
  }

  async loadStandings() {
    return this.withErrorBoundary(async () => {
      const seasonId = this.requireSeasonId(true);
      const standings = await apiRequest<StandingsReadDto>(`/seasons/${seasonId}/standings`);
      this.cache.standings = standings.driverStandings.map(mapDriverStanding);
      this.cache.constructorStandings = standings.constructorStandings.map(mapConstructorStanding);
      return this.cache.standings;
    });
  }

  private async runSession<TResponse>(session: SessionType, options: { stageId?: string } = {}) {
    const seasonId = this.requireSeasonId(true);
    const stageId = options.stageId ?? this.requireStageId();
    return apiRequest<TResponse>(`/seasons/${seasonId}/stages/${stageId}/${session}/run`, {
      method: "POST"
    });
  }

  private async readSessionResults<TResponse>(session: SessionType, stageIdOverride?: string) {
    const seasonId = this.requireSeasonId(true);
    const stageId = stageIdOverride ?? this.requireStageId();
    return apiRequest<TResponse>(`/seasons/${seasonId}/stages/${stageId}/${session}`);
  }

  private async readSessionResultsOrEmpty<TResponse>(
    session: SessionType,
    stageIdOverride?: string
  ) {
    try {
      return await this.readSessionResults<TResponse>(session, stageIdOverride);
    } catch (error) {
      if (error instanceof ApiError && error.code === "ENTITY_NOT_FOUND") {
        return null;
      }

      throw error;
    }
  }

  private applyCatalog(catalog: CatalogReadDto) {
    this.cache.drivers = catalog.drivers.map(mapDriver);
    this.cache.teams = catalog.teams.map(mapTeam);
    this.cache.tracks = catalog.tracks.map(mapTrack);

    if (!this.cache.stages.length) {
      this.cache.stages = catalog.calendar.map((stage) => ({
        id: `calendar-${stage.trackId}`,
        stageNumber: stage.stageNumber,
        trackId: stage.trackId,
        status: stage.stageNumber === 1 ? "available" : "locked",
        weekendDate: stage.weekendDate
      }));
    }
  }

  private applySeason(season: SeasonReadDto) {
    const mappedSeason = mapSeason(season);
    this.cache.activeSeason = mappedSeason;
    this.cache.currentUser = {
      ...this.cache.currentUser,
      selectedTeamId: season.selectedTeamId,
      activeSeasonId: season.id
    };
    this.cache.stages = season.stages.map(mapStage);
    this.cache.cars = season.cars.map(mapCar);
    this.cache.budget = mapBudget(season.budget, season.budgetTransactions);
    this.cache.practicePrograms = {
      ...this.cache.practicePrograms,
      ...Object.fromEntries(
        mappedSeason.stageProgress
          .filter((progress) => progress.practiceProgram)
          .map((progress) => [progress.stageId, progress.practiceProgram as PracticeProgram])
      )
    };
  }

  private applyPracticeProgram(response: {
    practiceProgram?: PracticeProgram | null;
    practiceResults: PracticeRunResponseDto["practiceResults"];
    stage: { id: string };
  }) {
    if (response.practiceProgram) {
      this.cache.practicePrograms[response.stage.id] = response.practiceProgram;
    }

    const otherStageResults = this.cache.practiceResults.filter(
      (result) => result.stageId !== response.stage.id
    );
    const stageResults = response.practiceResults.map(mapPracticeResult);
    this.cache.practiceResults = sortPracticeResults([...otherStageResults, ...stageResults]);
  }

  private replaceRaceResultsForStage(stageId: string, stageResults: RaceResult[]) {
    const otherStageResults = this.cache.raceResults.filter((result) => result.stageId !== stageId);
    this.cache.raceResults = sortByPosition([...otherStageResults, ...stageResults]);
  }

  private clearSeasonProtocolCache() {
    this.cache.practicePrograms = {};
    this.cache.practiceResults = [];
    this.cache.qualifyingResults = [];
    this.cache.raceResults = [];
    this.cache.standings = [];
    this.cache.constructorStandings = [];
  }

  private requireSeasonId(required: true): string;
  private requireSeasonId(required: false): string | null;
  private requireSeasonId(required: boolean) {
    const seasonId = this.cache.activeSeason?.id ?? this.cache.currentUser.activeSeasonId;

    if (!seasonId && required) {
      throw new Error("No active backend season is available.");
    }

    return seasonId ?? null;
  }

  private requireStageId() {
    const stageId = this.cache.activeSeason?.currentStageId;

    if (!stageId) {
      throw new Error("No active backend stage is available.");
    }

    return stageId;
  }

  private async withErrorBoundary<T>(operation: () => Promise<T>) {
    try {
      this.cache.lastError = null;
      return await operation();
    } catch (error) {
      if (error instanceof ApiError) {
        this.cache.lastError = error;
      }

      throw error;
    }
  }
}

export const backendSeasonRepository = new BackendSeasonRepository();
