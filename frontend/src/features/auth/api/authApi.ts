import { apiAuthRequest, apiRequest, apiRequestBlob } from "@/features/season/api/apiClient";
import type {
  AcceptedResponseDto,
  AuthLoginRequestDto,
  AuthRegisterRequestDto,
  AuthResponseDto,
  ChangePasswordRequestDto,
  DeleteAccountRequestDto,
  EmailRequestDto,
  LegalAcceptanceRequestDto,
  LegalAcceptanceStatusReadDto,
  LegalDocumentContentReadDto,
  LegalDocumentReadDto,
  PasswordResetChallengeDto,
  PasswordResetResendRequestDto,
  PublicLegalDocumentKind,
  ProfileReadDto,
  RegistrationChallengeDto,
  RegistrationConfirmationRequestDto,
  RegistrationResendRequestDto,
  ResetPasswordRequestDto,
  UpdateMeRequestDto,
  UserReadDto
} from "@/features/season/api/backendDtos";

export function loginRequest(payload: AuthLoginRequestDto) {
  return apiAuthRequest<AuthResponseDto>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function registerRequest(payload: AuthRegisterRequestDto) {
  return apiAuthRequest<RegistrationChallengeDto>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getActiveLegalDocuments() {
  return apiAuthRequest<LegalDocumentReadDto[]>("/legal/documents/active", { method: "GET" });
}

export function getPublicLegalDocument(kind: PublicLegalDocumentKind) {
  return apiAuthRequest<LegalDocumentContentReadDto>(`/legal/documents/${kind}`, { method: "GET" });
}

export function resendVerification(payload: RegistrationResendRequestDto) {
  return apiAuthRequest<AcceptedResponseDto>("/auth/registration/resend", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function confirmRegistration(payload: RegistrationConfirmationRequestDto) {
  return apiAuthRequest<AcceptedResponseDto>("/auth/registration/confirm", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function forgotPassword(payload: EmailRequestDto) {
  return apiAuthRequest<PasswordResetChallengeDto>("/auth/password/forgot", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function resendPasswordReset(payload: PasswordResetResendRequestDto) {
  return apiAuthRequest<AcceptedResponseDto>("/auth/password/resend", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function resetPassword(payload: ResetPasswordRequestDto) {
  return apiAuthRequest<AcceptedResponseDto>("/auth/password/reset", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getLegalAcceptanceStatus() {
  return apiRequest<LegalAcceptanceStatusReadDto[]>("/legal/acceptances/me", { method: "GET" });
}

export function acceptLegalDocuments(payload: LegalAcceptanceRequestDto[]) {
  return apiRequest<void>("/legal/acceptances", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function exportMyData() {
  return apiRequestBlob("/auth/me/export", { method: "GET" });
}

export function refreshRequest() {
  return apiAuthRequest<AuthResponseDto>("/auth/refresh", {
    method: "POST"
  });
}

export function getProfile() {
  return apiRequest<ProfileReadDto>("/auth/profile", { method: "GET" });
}

export function updateMe(payload: UpdateMeRequestDto) {
  return apiRequest<UserReadDto>("/auth/me", {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export function changePassword(payload: ChangePasswordRequestDto) {
  return apiRequest<void>("/auth/me/password", {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export function deleteAccount(payload: DeleteAccountRequestDto) {
  return apiRequest<void>("/auth/me", {
    method: "DELETE",
    body: JSON.stringify(payload)
  });
}

export async function logoutRequest() {
  await fetch("/api/v1/auth/logout", {
    method: "POST",
    credentials: "include"
  });
}
