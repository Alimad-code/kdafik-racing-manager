import {
  clearAccessToken,
  getAccessToken,
  notifyAuthExpired,
  setAccessToken
} from "@/features/auth/model/authSession";
import type { AuthResponseDto, BackendErrorResponse } from "@/features/season/api/backendDtos";

const API_BASE_URL = "/api/v1";

const ERROR_MESSAGES: Record<string, string> = {
  DISPLAY_NAME_ALREADY_REGISTERED: "Display name is already registered.",
  DUPLICATE_DRIVER: "The same driver cannot be selected twice.",
  EMAIL_ALREADY_REGISTERED: "Email is already registered.",
  EMAIL_NOT_VERIFIED: "Подтвердите email, прежде чем входить.",
  INVALID_EMAIL_ACTION_CODE: "Код недействителен или срок его действия истёк.",
  LEGAL_DOCUMENTS_UNAVAILABLE:
    "Не удалось загрузить обязательные документы. Попробуйте ещё раз позже.",
  INVALID_LEGAL_ACCEPTANCE: "Необходимо подтвердить все актуальные документы.",
  EMAIL_DELIVERY_UNAVAILABLE: "Письмо сейчас не удалось отправить. Попробуйте позже.",
  ENTITY_NOT_FOUND: "The requested season data is not available yet.",
  FORBIDDEN: "This account does not have access to the requested data.",
  INSUFFICIENT_FUNDS: "Недостаточно средств для этого действия.",
  INVALID_CREDENTIALS: "Invalid login or password.",
  INVALID_TOKEN: "Sign in again to continue.",
  INVALID_ROSTER: "The selected roster is incomplete or invalid.",
  INVALID_STATE_TRANSITION: "The backend rejected this season state transition.",
  NETWORK_ERROR: "Не удалось подключиться к сервису. Проверьте соединение и повторите попытку.",
  RATE_LIMITED: "Слишком много попыток. Подождите и повторите.",
  PREVIOUS_SESSION_NOT_COMPLETED: "The previous session has not been completed yet.",
  SEASON_ALREADY_FINISHED: "This season is already finished.",
  SEASON_NOT_IN_PROGRESS: "This season is not in progress yet.",
  SESSION_ALREADY_COMPLETED: "This session has already been completed.",
  STAGE_LOCKED: "This stage is still locked.",
  UNAUTHORIZED: "Sign in again to continue.",
  VALIDATION_ERROR: "The backend rejected the request validation."
};

function getSafeErrorMessage(status: number, error: BackendErrorResponse) {
  if (ERROR_MESSAGES[error.code]) {
    return ERROR_MESSAGES[error.code];
  }

  if (status === 0) {
    return ERROR_MESSAGES.NETWORK_ERROR;
  }

  return "Не удалось выполнить запрос. Попробуйте ещё раз.";
}

export class ApiError extends Error {
  code: string;
  details: Record<string, unknown>;
  rawMessage: string;
  status: number;

  constructor(status: number, error: BackendErrorResponse) {
    super(getSafeErrorMessage(status, error));
    this.name = "ApiError";
    this.status = status;
    this.code = error.code || "HTTP_ERROR";
    this.details = error.details ?? {};
    this.rawMessage = error.message;
  }
}

async function parseErrorResponse(response: Response, path: string) {
  const fallback: BackendErrorResponse = {
    code: response.status === 401 ? "UNAUTHORIZED" : "HTTP_ERROR",
    message: `Backend request failed with HTTP ${response.status}.`,
    details: { path }
  };

  try {
    const text = await response.text();
    const error = JSON.parse(text) as BackendErrorResponse;
    return error.code && error.message ? error : fallback;
  } catch {
    return fallback;
  }
}

async function fetchJson<TResponse>(path: string, init: RequestInit = {}) {
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...init.headers
      }
    });
  } catch {
    throw new ApiError(0, {
      code: "NETWORK_ERROR",
      message: "FastAPI is unreachable.",
      details: { path }
    });
  }

  if (!response.ok) {
    throw new ApiError(response.status, await parseErrorResponse(response, path));
  }

  if (response.status === 204) {
    return undefined as TResponse;
  }

  return (await response.json()) as TResponse;
}

export async function apiAuthRequest<TResponse>(
  path: string,
  init: RequestInit = {}
): Promise<TResponse> {
  return fetchJson<TResponse>(path, {
    ...init,
    credentials: "include"
  });
}

export async function apiAuthRequestNoContent(path: string, init: RequestInit = {}) {
  await fetchJson<void>(path, {
    ...init,
    credentials: "include",
    // A 204 response has no JSON body; fetchJson handles this marker explicitly.
    headers: { ...init.headers }
  });
}

export async function refreshAuthToken() {
  const response = await apiAuthRequest<AuthResponseDto>("/auth/refresh", {
    method: "POST"
  });
  setAccessToken(response.accessToken);
  return response;
}

export async function apiRequest<TResponse>(
  path: string,
  init: RequestInit = {}
): Promise<TResponse> {
  const token = getAccessToken();

  try {
    return await fetchJson<TResponse>(path, {
      ...init,
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init.headers
      }
    });
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) {
      throw error;
    }

    try {
      const refreshed = await refreshAuthToken();
      return await fetchJson<TResponse>(path, {
        ...init,
        headers: {
          Authorization: `Bearer ${refreshed.accessToken}`,
          ...init.headers
        }
      });
    } catch (refreshError) {
      clearAccessToken();
      notifyAuthExpired();
      throw refreshError;
    }
  }
}

export async function apiRequestBlob(path: string, init: RequestInit = {}) {
  const request = async (token: string | null) => {
    let response: Response;
    try {
      response = await fetch(`${API_BASE_URL}${path}`, {
        ...init,
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...init.headers
        }
      });
    } catch {
      throw new ApiError(0, {
        code: "NETWORK_ERROR",
        message: "FastAPI is unreachable.",
        details: { path }
      });
    }
    if (!response.ok) throw new ApiError(response.status, await parseErrorResponse(response, path));
    return {
      blob: await response.blob(),
      contentDisposition: response.headers.get("Content-Disposition")
    };
  };

  try {
    return await request(getAccessToken());
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) throw error;
    try {
      const refreshed = await refreshAuthToken();
      return await request(refreshed.accessToken);
    } catch (refreshError) {
      clearAccessToken();
      notifyAuthExpired();
      throw refreshError;
    }
  }
}
