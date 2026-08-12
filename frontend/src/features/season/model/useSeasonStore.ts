import { create } from "zustand";
import type { BudgetState, Car, PracticeSegment, StageSessionProgress } from "@/entities";
import { ApiError } from "@/features/season/api/apiClient";
import { seasonRepository } from "@/features/season/api/seasonDataSource";

const emptyBudget: BudgetState = {
  startingMillions: 0,
  spentMillions: 0,
  availableMillions: 0,
  repairReserveMillions: 0,
  setupReserveMillions: 0,
  freeMillions: 0,
  transactions: []
};

type SeasonStoreState = {
  activeSeasonId: string | null;
  selectedTeamId: string | null;
  selectedDriverIds: string[];
  currentStageId: string;
  cars: Car[];
  originalCars: Car[];
  stageProgress: StageSessionProgress[];
  budget: BudgetState;
  isBootstrapped: boolean;
  isLoading: boolean;
  errorCode: string | null;
  errorMessage: string | null;
  version: number;
  bootstrap: () => Promise<void>;
  refreshSeason: () => Promise<void>;
  startNewSeason: () => Promise<void>;
  selectTeam: (teamId: string) => void;
  setDrivers: (driverIds: string[]) => void;
  confirmRoster: () => Promise<void>;
  setCarSetup: (
    carId: string,
    params: Partial<{
      wings: number;
      suspension: number;
      gearbox: number;
    }>
  ) => void;
  resetCarSetup: (carId: string) => void;
  saveCarSetups: (session: "practice" | "qualifying" | "race", stageId?: string) => Promise<void>;
  runPracticeSegment: (segment: PracticeSegment) => Promise<void>;
  completePractice: () => Promise<void>;
  restorePracticeProgram: () => Promise<void>;
  runQualifying: () => Promise<void>;
  restoreQualifyingResults: () => Promise<void>;
  restoreRaceResults: (stageId?: string, options?: { waitForAutosave?: boolean }) => Promise<void>;
  repairCar: (carId: string) => Promise<void>;
  loadStandings: () => Promise<void>;
  resetSessionState: () => void;
  clearError: () => void;
};

const initialSeasonState = {
  activeSeasonId: null,
  selectedTeamId: null,
  selectedDriverIds: [],
  currentStageId: "",
  cars: [],
  originalCars: [],
  stageProgress: [],
  budget: emptyBudget,
  isBootstrapped: false,
  isLoading: false,
  errorCode: null,
  errorMessage: null
};

function snapshotFromRepository() {
  const activeSeason = seasonRepository.getActiveSeason();

  return {
    activeSeasonId: activeSeason?.id || null,
    selectedTeamId: activeSeason?.selectedTeamId || null,
    selectedDriverIds: activeSeason?.selectedDriverIds ?? [],
    currentStageId: activeSeason?.currentStageId ?? seasonRepository.getStages()[0]?.id ?? "",
    cars: seasonRepository.getCars(),
    originalCars: seasonRepository.getCars(),
    stageProgress: activeSeason?.stageProgress ?? [],
    budget: seasonRepository.getBudget()
  };
}

function getErrorState(error: unknown) {
  if (error instanceof ApiError) {
    return {
      errorCode: error.code,
      errorMessage: error.message
    };
  }

  return {
    errorCode: "UNKNOWN_ERROR",
    errorMessage: error instanceof Error ? error.message : "Unexpected frontend error."
  };
}

function toSetupPayload(cars: Car[]) {
  return cars.map((car) => ({
    carId: car.id,
    wingsSetting: car.wingsSetting,
    suspensionSetting: car.suspensionSetting,
    gearboxSetting: car.gearboxSetting
  }));
}

async function runBackendAction(
  set: (partial: Partial<SeasonStoreState>) => void,
  get: () => SeasonStoreState,
  action: () => Promise<void>
) {
  set({ isLoading: true, errorCode: null, errorMessage: null });

  try {
    await action();
    set({
      ...snapshotFromRepository(),
      isLoading: false,
      version: get().version + 1
    });
  } catch (error) {
    set({
      ...getErrorState(error),
      isLoading: false,
      version: get().version + 1
    });
    throw error;
  }
}

export const useSeasonStore = create<SeasonStoreState>((set, get) => ({
  ...initialSeasonState,
  version: 0,
  bootstrap: async () => {
    await runBackendAction(set, get, async () => {
      await seasonRepository.bootstrap();

      if (!seasonRepository.getActiveSeason()) {
        await seasonRepository.createSeason();
      }
    });

    set({ isBootstrapped: true });
  },
  refreshSeason: async () =>
    runBackendAction(set, get, async () => {
      await seasonRepository.refreshSeason();
    }),
  startNewSeason: async () =>
    runBackendAction(set, get, async () => {
      await seasonRepository.startNewSeason();
    }),
  selectTeam: (teamId) => set({ selectedTeamId: teamId }),
  setDrivers: (driverIds) => set({ selectedDriverIds: driverIds.slice(0, 2) }),
  confirmRoster: async () => {
    const { selectedDriverIds, selectedTeamId } = get();

    if (!selectedTeamId || selectedDriverIds.length !== 2) {
      return;
    }

    await runBackendAction(set, get, async () => {
      await seasonRepository.confirmRoster(selectedDriverIds, selectedTeamId);
    });
  },
  setCarSetup: (carId, params) =>
    set((state) => ({
      cars: state.cars.map((car) =>
        car.id === carId
          ? {
              ...car,
              wingsSetting:
                params.wings !== undefined
                  ? Math.max(0, Math.min(100, Math.round(params.wings)))
                  : car.wingsSetting,
              suspensionSetting:
                params.suspension !== undefined
                  ? Math.max(0, Math.min(100, Math.round(params.suspension)))
                  : car.suspensionSetting,
              gearboxSetting:
                params.gearbox !== undefined
                  ? Math.max(0, Math.min(100, Math.round(params.gearbox)))
                  : car.gearboxSetting
            }
          : car
      )
    })),
  resetCarSetup: (carId) =>
    set((state) => ({
      cars: state.cars.map((car) => {
        if (car.id !== carId) return car;
        const originalCar = state.originalCars.find((oc) => oc.id === carId);
        return originalCar
          ? {
              ...car,
              wingsSetting: originalCar.wingsSetting,
              suspensionSetting: originalCar.suspensionSetting,
              gearboxSetting: originalCar.gearboxSetting
            }
          : car;
      })
    })),
  saveCarSetups: async (session, stageId) =>
    runBackendAction(set, get, async () => {
      await seasonRepository.saveCarSetups(session, toSetupPayload(get().cars), stageId);
    }),
  runPracticeSegment: async (segment) =>
    runBackendAction(set, get, async () => {
      await seasonRepository.saveCarSetups("practice", toSetupPayload(get().cars));
      await seasonRepository.runPracticeSegment(segment);
    }),
  completePractice: async () =>
    runBackendAction(set, get, async () => {
      await seasonRepository.saveCarSetups("practice", toSetupPayload(get().cars));
      await seasonRepository.completePractice();
    }),
  restorePracticeProgram: async () =>
    runBackendAction(set, get, async () => {
      await seasonRepository.readPracticeProgram();
    }),
  runQualifying: async () =>
    runBackendAction(set, get, async () => {
      await seasonRepository.saveCarSetups("qualifying", toSetupPayload(get().cars));
      await seasonRepository.runQualifying();
    }),
  restoreQualifyingResults: async () =>
    runBackendAction(set, get, async () => {
      await seasonRepository.readQualifyingResults();
    }),
  restoreRaceResults: async (stageId, options) =>
    runBackendAction(set, get, async () => {
      await seasonRepository.readRaceResults(stageId, options);
    }),
  repairCar: async (carId) =>
    runBackendAction(set, get, async () => {
      await seasonRepository.repairCar(carId);
    }),
  loadStandings: async () =>
    runBackendAction(set, get, async () => {
      await seasonRepository.loadStandings();
    }),
  resetSessionState: () =>
    set((state) => ({
      ...initialSeasonState,
      version: state.version + 1
    })),
  clearError: () => set({ errorCode: null, errorMessage: null })
}));
