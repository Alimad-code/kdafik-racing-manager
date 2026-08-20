import { create } from "zustand";
import type { User } from "@/entities";
import { ApiError } from "@/features/season/api/apiClient";
import { seasonRepository } from "@/features/season/api/seasonDataSource";
import type {
  AuthLoginRequestDto,
  AuthRegisterRequestDto,
  AuthResponseDto,
  RegistrationChallengeDto
} from "@/features/season/api/backendDtos";
import {
  loginRequest,
  logoutRequest,
  refreshRequest,
  registerRequest
} from "@/features/auth/api/authApi";
import { clearAccessToken, setAccessToken } from "@/features/auth/model/authSession";

type AuthStatus = "idle" | "checking" | "authenticated" | "anonymous";

type AuthStoreState = {
  activeSeasonId: string | null;
  errorCode: string | null;
  errorMessage: string | null;
  isLoading: boolean;
  status: AuthStatus;
  user: User | null;
  login: (payload: AuthLoginRequestDto) => Promise<AuthResponseDto>;
  register: (payload: AuthRegisterRequestDto) => Promise<RegistrationChallengeDto>;
  refresh: () => Promise<AuthResponseDto | null>;
  logout: () => Promise<void>;
  updateUser: (user: User) => void;
  clearError: () => void;
  markAnonymous: () => void;
};

function getErrorState(error: unknown) {
  if (error instanceof ApiError) {
    return {
      errorCode: error.code,
      errorMessage: error.message
    };
  }

  return {
    errorCode: "UNKNOWN_ERROR",
    errorMessage: error instanceof Error ? error.message : "Unexpected auth error."
  };
}

function applyAuthResponse(response: AuthResponseDto) {
  setAccessToken(response.accessToken);
  seasonRepository.syncAuthSession(response);
  return {
    activeSeasonId: response.activeSeasonId,
    errorCode: null,
    errorMessage: null,
    isLoading: false,
    status: "authenticated" as const,
    user: seasonRepository.getCurrentUser()
  };
}

function isSilentInitialRefreshFailure(error: unknown) {
  return error instanceof ApiError && (error.status === 401 || error.code === "INVALID_TOKEN");
}

export const useAuthStore = create<AuthStoreState>((set) => ({
  activeSeasonId: null,
  errorCode: null,
  errorMessage: null,
  isLoading: false,
  status: "idle",
  user: null,
  login: async (payload) => {
    set({ errorCode: null, errorMessage: null, isLoading: true });

    try {
      const response = await loginRequest(payload);
      set(applyAuthResponse(response));
      return response;
    } catch (error) {
      set({
        ...getErrorState(error),
        isLoading: false,
        status: "anonymous"
      });
      throw error;
    }
  },
  register: async (payload) => {
    set({ errorCode: null, errorMessage: null, isLoading: true });

    try {
      const response = await registerRequest(payload);
      clearAccessToken();
      seasonRepository.clearSession();
      set({ errorCode: null, errorMessage: null, isLoading: false, status: "anonymous" });
      return response;
    } catch (error) {
      set({
        ...getErrorState(error),
        isLoading: false,
        status: "anonymous"
      });
      throw error;
    }
  },
  refresh: async () => {
    set({ errorCode: null, errorMessage: null, isLoading: true, status: "checking" });

    try {
      const response = await refreshRequest();
      set(applyAuthResponse(response));
      return response;
    } catch (error) {
      clearAccessToken();
      seasonRepository.clearSession();
      if (isSilentInitialRefreshFailure(error)) {
        set({
          activeSeasonId: null,
          errorCode: null,
          errorMessage: null,
          isLoading: false,
          status: "anonymous",
          user: null
        });
        return null;
      }
      set({
        ...getErrorState(error),
        activeSeasonId: null,
        isLoading: false,
        status: "anonymous",
        user: null
      });
      return null;
    }
  },
  logout: async () => {
    set({ isLoading: true });

    try {
      await logoutRequest();
    } finally {
      clearAccessToken();
      seasonRepository.clearSession();
      set({
        activeSeasonId: null,
        errorCode: null,
        errorMessage: null,
        isLoading: false,
        status: "anonymous",
        user: null
      });
    }
  },
  updateUser: (user) => {
    seasonRepository.updateCurrentUser(user);
    set({ user });
  },
  clearError: () => set({ errorCode: null, errorMessage: null }),
  markAnonymous: () => {
    clearAccessToken();
    seasonRepository.clearSession();
    set({
      activeSeasonId: null,
      errorCode: "UNAUTHORIZED",
      errorMessage: "Sign in again to continue.",
      isLoading: false,
      status: "anonymous",
      user: null
    });
  }
}));
