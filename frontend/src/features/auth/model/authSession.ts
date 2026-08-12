let accessToken: string | null = null;

export const AUTH_EXPIRED_EVENT = "kdafik-auth-expired";

export function getAccessToken() {
  return accessToken;
}

export function setAccessToken(nextAccessToken: string | null) {
  accessToken = nextAccessToken;
}

export function clearAccessToken() {
  accessToken = null;
}

export function notifyAuthExpired() {
  clearAccessToken();
  window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
}
