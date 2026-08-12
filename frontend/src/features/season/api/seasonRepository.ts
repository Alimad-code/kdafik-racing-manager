import type {
  BudgetState,
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
import type { ApiError } from "@/features/season/api/apiClient";
import type { AuthResponseDto } from "@/features/season/api/backendDtos";

export type SeasonRepository = {
  getCurrentUser: () => User;
  updateCurrentUser: (user: User) => void;
  getActiveSeason: () => Season | null;
  getDrivers: () => Driver[];
  getTeams: () => Team[];
  getTracks: () => Track[];
  getStages: () => SeasonStage[];
  getCars: () => Car[];
  getBudget: () => BudgetState;
  getPracticeResults: () => PracticeResult[];
  getPracticeResultsByStage: (stageId: string) => PracticeResult[];
  getPracticeProgramByStage: (stageId: string) => PracticeProgram | null;
  getQualifyingResults: () => QualifyingResult[];
  getQualifyingResultsByStage: (stageId: string) => QualifyingResult[];
  getRaceResults: () => RaceResult[];
  getRaceResultsByStage: (stageId: string) => RaceResult[];
  getChampionshipStandings: () => ChampionshipStanding[];
  getConstructorStandings: () => ConstructorStanding[];
  syncAuthSession: (authSession: AuthResponseDto) => void;
  clearSession: () => void;
  bootstrap: () => Promise<void>;
  createSeason: () => Promise<Season>;
  refreshSeason: () => Promise<Season | null>;
  startNewSeason: () => Promise<Season>;
  confirmRoster: (driverIds: string[], teamId: string) => Promise<Season>;
  saveCarSetups: (
    session: SessionType,
    setups?: Array<{
      carId: string;
      wingsSetting: number;
      suspensionSetting: number;
      gearboxSetting: number;
    }>,
    stageId?: string
  ) => Promise<Season>;
  readCarSetups: (session: SessionType) => Promise<Season>;
  runPracticeSegment: (segment: PracticeSegment) => Promise<PracticeResult[]>;
  completePractice: () => Promise<PracticeProgram>;
  readPracticeProgram: () => Promise<PracticeResult[]>;
  runQualifying: () => Promise<QualifyingResult[]>;
  readQualifyingResults: () => Promise<QualifyingResult[]>;
  readRaceResults: (
    stageId?: string,
    options?: { waitForAutosave?: boolean }
  ) => Promise<RaceResult[]>;
  repairCar: (carId: string) => Promise<Car>;
  loadStandings: () => Promise<ChampionshipStanding[]>;
  getLastError: () => ApiError | null;
  clearLastError: () => void;
};
