import { FormEvent, useEffect, useState } from "react";
import { Eye, EyeOff, LockKeyhole } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { getActiveLegalDocuments, resendVerification } from "@/features/auth/api/authApi";
import { useAuthStore } from "@/features/auth/model/useAuthStore";
import { ApiError } from "@/features/season/api/apiClient";
import type { LegalDocumentKind, LegalDocumentReadDto } from "@/features/season/api/backendDtos";
import { seasonRepository } from "@/features/season/api/seasonDataSource";
import { useSeasonStore } from "@/features/season/model/useSeasonStore";
import { ROUTES } from "@/shared/constants/routes";
import { cn } from "@/shared/lib/utils";
import { Button, KdafikLogo, LegalFooter } from "@/shared/ui";

type AuthMode = "login" | "register";
type LegalChecks = Record<LegalDocumentKind, boolean>;

const REQUIRED_KINDS: LegalDocumentKind[] = [
  "privacy_policy",
  "personal_data_consent",
  "user_agreement"
];

const EMPTY_CHECKS: LegalChecks = {
  privacy_policy: false,
  personal_data_consent: false,
  user_agreement: false
};

const RESEND_COOLDOWN_SECONDS = 60;

function maskEmail(value: string) {
  const [localPart, domain] = value.split("@");
  if (!localPart || !domain) return value;
  if (localPart.length <= 2) return `${localPart[0] ?? ""}*@${domain}`;
  return `${localPart.slice(0, 2)}${"*".repeat(Math.max(2, localPart.length - 2))}@${domain}`;
}

function getPostAuthRoute() {
  const activeSeason = seasonRepository.getActiveSeason();
  return activeSeason?.status === "setup" ? ROUTES.seasonSetup : ROUTES.home;
}

function getAuthErrorMessage(code: string | null) {
  switch (code) {
    case "INVALID_CREDENTIALS":
      return "Неверный email, имя профиля или пароль.";
    case "EMAIL_NOT_VERIFIED":
      return "Подтвердите email, прежде чем входить.";
    case "EMAIL_ALREADY_REGISTERED":
      return "Этот email уже зарегистрирован.";
    case "DISPLAY_NAME_ALREADY_REGISTERED":
      return "Это имя профиля уже зарегистрировано.";
    case "LEGAL_DOCUMENTS_UNAVAILABLE":
      return "Не удалось загрузить обязательные документы. Повторите попытку позже.";
    case "INVALID_LEGAL_ACCEPTANCE":
      return "Необходимо подтвердить каждый обязательный документ.";
    case "EMAIL_DELIVERY_UNAVAILABLE":
      return "Письмо сейчас не удалось отправить. Попробуйте позже.";
    case "NETWORK_ERROR":
      return "Не удалось подключиться к сервису. Проверьте соединение и повторите попытку.";
    case "RATE_LIMITED":
      return "Слишком много попыток. Подождите и повторите.";
    default:
      return null;
  }
}

export function LoginPage() {
  const navigate = useNavigate();
  const login = useAuthStore((state) => state.login);
  const register = useAuthStore((state) => state.register);
  const authStatus = useAuthStore((state) => state.status);
  const authErrorCode = useAuthStore((state) => state.errorCode);
  const authIsLoading = useAuthStore((state) => state.isLoading);
  const clearAuthError = useAuthStore((state) => state.clearError);
  const bootstrap = useSeasonStore((state) => state.bootstrap);
  const resetSessionState = useSeasonStore((state) => state.resetSessionState);
  const [mode, setMode] = useState<AuthMode>("login");
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isPasswordVisible, setIsPasswordVisible] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [documents, setDocuments] = useState<LegalDocumentReadDto[] | null>(null);
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [documentsError, setDocumentsError] = useState<string | null>(null);
  const [checks, setChecks] = useState<LegalChecks>(EMPTY_CHECKS);
  const [registrationComplete, setRegistrationComplete] = useState(false);
  const [resendMessage, setResendMessage] = useState<string | null>(null);
  const [resending, setResending] = useState(false);
  const [resendAvailableAt, setResendAvailableAt] = useState<number | null>(null);
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    resetSessionState();
  }, [resetSessionState]);

  async function loadDocuments() {
    setDocumentsLoading(true);
    setDocumentsError(null);
    try {
      const nextDocuments = await getActiveLegalDocuments();
      const kinds = new Set(nextDocuments.map((document) => document.kind));
      if (nextDocuments.length !== 3 || REQUIRED_KINDS.some((kind) => !kinds.has(kind))) {
        throw new Error("incomplete");
      }
      setDocuments(nextDocuments);
    } catch {
      setDocuments(null);
      setDocumentsError("Обязательные документы временно недоступны. Повторите загрузку позже.");
    } finally {
      setDocumentsLoading(false);
    }
  }

  useEffect(() => {
    if (mode === "register" && !documents && !documentsLoading && !documentsError)
      void loadDocuments();
  }, [mode, documents, documentsError, documentsLoading]);

  useEffect(() => {
    if (!resendAvailableAt) return;
    const interval = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(interval);
  }, [resendAvailableAt]);

  function switchMode(nextMode: AuthMode) {
    setMode(nextMode);
    setLocalError(null);
    setRegistrationComplete(false);
    setResendMessage(null);
    setResendAvailableAt(null);
    clearAuthError();
  }

  async function sendVerification(emailValue: string) {
    setResending(true);
    try {
      await resendVerification({ email: emailValue.trim() });
    } catch {
      // The result remains deliberately generic to avoid account enumeration.
    } finally {
      setResending(false);
      setResendAvailableAt(Date.now() + RESEND_COOLDOWN_SECONDS * 1000);
      setResendMessage("Если адрес подходит, письмо с подтверждением будет отправлено.");
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLocalError(null);
    clearAuthError();
    const trimmedLogin = email.trim();
    const trimmedDisplayName = displayName.trim();
    if (!trimmedLogin || !password) {
      setLocalError(
        mode === "register" ? "Введите email и пароль." : "Введите email или имя профиля и пароль."
      );
      return;
    }
    if (mode === "register" && !trimmedDisplayName) {
      setLocalError("Укажите имя профиля.");
      return;
    }
    if (mode === "register" && password.length < 8) {
      setLocalError("Пароль должен быть не короче 8 символов.");
      return;
    }
    if (mode === "register" && (!documents || REQUIRED_KINDS.some((kind) => !checks[kind]))) {
      setLocalError("Подтвердите каждый обязательный документ.");
      return;
    }
    try {
      if (mode === "register" && documents) {
        await register({
          displayName: trimmedDisplayName,
          email: trimmedLogin,
          password,
          legalAcceptances: documents.map((document) => ({
            kind: document.kind,
            version: document.version,
            accepted: checks[document.kind]
          }))
        });
        setRegistrationComplete(true);
        setPassword("");
        setResendAvailableAt(Date.now() + RESEND_COOLDOWN_SECONDS * 1000);
        return;
      }
      await login({ login: trimmedLogin, password });
      await bootstrap();
      navigate(getPostAuthRoute(), { replace: true });
    } catch (error) {
      if (error instanceof ApiError && error.code === "EMAIL_NOT_VERIFIED") {
        setLocalError("Подтвердите email. Можно повторно запросить письмо ниже.");
      }
    }
  }

  const errorMessage = localError ?? getAuthErrorMessage(authErrorCode);
  const isSubmitting = authIsLoading || authStatus === "checking";
  const isRegisterDisabled =
    isSubmitting || !documents || documentsLoading || REQUIRED_KINDS.some((kind) => !checks[kind]);
  const resendRemainingSeconds = resendAvailableAt
    ? Math.max(0, Math.ceil((resendAvailableAt - now) / 1000))
    : 0;
  const isResendCoolingDown = resendRemainingSeconds > 0;

  return (
    <main className="flex min-h-screen flex-col text-foreground">
      <section className="flex flex-1 items-center justify-center overflow-hidden px-3 py-4 sm:px-6 sm:py-6">
        <div className="race-panel w-full max-w-[560px] p-4 sm:p-6 lg:p-8">
          <div className="flex items-center gap-3 text-primary">
            <KdafikLogo className="h-5 w-20 shrink-0" />
            <span className="text-[11px] font-black uppercase tracking-[0.2em] sm:text-xs sm:tracking-[0.28em]">
              Kdafik Racing Manager
            </span>
          </div>
          <div className="mt-5">
            <h1 className="text-3xl font-black uppercase leading-none tracking-tight sm:text-4xl">
              {mode === "register" ? "Регистрация команды" : "Вход в гоночный штаб"}
            </h1>
            <p className="mt-4 max-w-xl text-sm leading-6 text-muted-foreground">
              Войдите в существующий профиль или создайте новый, чтобы продолжить сезон.
            </p>
          </div>
          <div className="mt-6 grid grid-cols-2 gap-2 border border-border bg-background p-1">
            {(["login", "register"] as const).map((item) => (
              <button
                key={item}
                className={cn(
                  "min-h-10 px-3 font-mono text-xs font-black uppercase tracking-[0.14em] transition",
                  mode === item
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                )}
                type="button"
                onClick={() => switchMode(item)}
              >
                {item === "login" ? "Вход" : "Регистрация"}
              </button>
            ))}
          </div>
          {registrationComplete ? (
            <div className="mt-6 grid gap-4" role="status">
              <p className="text-sm leading-6">
                Письмо отправлено на <strong>{maskEmail(email)}</strong>. Ссылка действует 24 часа;
                для входа необходимо подтвердить адрес из письма.
              </p>
              <Button
                type="button"
                disabled={resending || isResendCoolingDown}
                onClick={() => void sendVerification(email)}
              >
                {resending
                  ? "Отправляем..."
                  : isResendCoolingDown
                    ? `Повторная отправка через ${resendRemainingSeconds} с`
                    : "Отправить письмо повторно"}
              </Button>
              {resendMessage ? (
                <p className="text-sm text-muted-foreground">{resendMessage}</p>
              ) : null}
              <div className="flex flex-wrap gap-3">
                <Button
                  variant="secondary"
                  type="button"
                  onClick={() => setRegistrationComplete(false)}
                >
                  Изменить email
                </Button>
                <Button variant="secondary" type="button" onClick={() => switchMode("login")}>
                  Перейти ко входу
                </Button>
              </div>
            </div>
          ) : (
            <form className="mt-6 grid gap-4" onSubmit={handleSubmit}>
              {mode === "register" ? (
                <label className="grid gap-2" htmlFor="auth-display-name">
                  <span className="metadata-label">Имя профиля</span>
                  <input
                    id="auth-display-name"
                    className="min-h-11 border border-input bg-background px-3 font-mono text-sm font-bold text-foreground outline-none transition focus:border-primary"
                    autoComplete="nickname"
                    name="displayName"
                    type="text"
                    value={displayName}
                    onChange={(event) => setDisplayName(event.target.value)}
                  />
                </label>
              ) : null}
              <label className="grid gap-2" htmlFor="auth-login">
                <span className="metadata-label">
                  {mode === "register" ? "Email" : "Email или имя профиля"}
                </span>
                <input
                  id="auth-login"
                  className="min-h-11 border border-input bg-background px-3 font-mono text-sm font-bold text-foreground outline-none transition focus:border-primary"
                  autoComplete={mode === "register" ? "email" : "username"}
                  name={mode === "register" ? "email" : "login"}
                  type={mode === "register" ? "email" : "text"}
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </label>
              <div className="grid gap-2">
                <label className="metadata-label" htmlFor="auth-password">
                  Пароль
                </label>
                <div className="relative">
                  <input
                    id="auth-password"
                    className="min-h-11 w-full border border-input bg-background px-3 pr-12 font-mono text-sm font-bold text-foreground outline-none transition focus:border-primary"
                    autoComplete={mode === "register" ? "new-password" : "current-password"}
                    name="password"
                    type={isPasswordVisible ? "text" : "password"}
                    maxLength={128}
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                  />
                  <button
                    aria-label={
                      isPasswordVisible ? "Скрыть значение пароля" : "Показать значение пароля"
                    }
                    className="absolute right-1 top-1/2 grid size-9 -translate-y-1/2 place-items-center text-muted-foreground transition hover:bg-secondary hover:text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                    type="button"
                    onClick={() => setIsPasswordVisible((current) => !current)}
                  >
                    {isPasswordVisible ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                  </button>
                </div>
              </div>
              {mode === "register" ? (
                <fieldset
                  className="grid gap-3 border border-border p-3"
                  disabled={documentsLoading}
                >
                  <legend className="px-1 text-sm font-bold">Обязательные документы</legend>
                  {documentsLoading ? (
                    <p className="text-sm text-muted-foreground">Загружаем документы…</p>
                  ) : null}
                  {documentsError ? (
                    <div className="grid gap-2">
                      <p className="text-sm text-danger">{documentsError}</p>
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={() => void loadDocuments()}
                      >
                        Повторить загрузку
                      </Button>
                    </div>
                  ) : null}
                  {documents?.map((document) => (
                    <label key={document.kind} className="flex items-start gap-3 text-sm">
                      <input
                        type="checkbox"
                        checked={checks[document.kind]}
                        onChange={(event) =>
                          setChecks((current) => ({
                            ...current,
                            [document.kind]: event.target.checked
                          }))
                        }
                      />
                      <span>
                        Принимаю{" "}
                        <a
                          className="underline decoration-primary underline-offset-2"
                          href={document.publicPath}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {document.title} (версия {document.version})
                        </a>
                      </span>
                    </label>
                  ))}
                </fieldset>
              ) : null}
              {errorMessage ? (
                <div
                  className="border border-danger/30 bg-danger/10 p-3 text-sm font-semibold text-danger"
                  role="alert"
                >
                  {errorMessage}
                </div>
              ) : null}
              {mode === "login" ? (
                <div className="flex flex-wrap gap-3 text-sm">
                  <Link className="underline" to="/forgot-password">
                    Не помню пароль
                  </Link>
                  {authErrorCode === "EMAIL_NOT_VERIFIED" ||
                  localError?.includes("Подтвердите email") ? (
                    <button
                      className="underline"
                      type="button"
                      disabled={resending || isResendCoolingDown}
                      onClick={() => void sendVerification(email)}
                    >
                      {resending
                        ? "Отправляем..."
                        : isResendCoolingDown
                          ? `Повторная отправка через ${resendRemainingSeconds} с`
                          : "Отправить подтверждение повторно"}
                    </button>
                  ) : null}
                </div>
              ) : null}
              {resendMessage ? (
                <p className="text-sm text-muted-foreground" role="status">
                  {resendMessage}
                </p>
              ) : null}
              <Button
                className="w-full"
                disabled={mode === "register" ? isRegisterDisabled : isSubmitting}
                type="submit"
              >
                <LockKeyhole className="mr-2 size-4" />
                {isSubmitting
                  ? "Проверяем доступ..."
                  : mode === "register"
                    ? "Отправить письмо для подтверждения"
                    : "Войти"}
              </Button>
            </form>
          )}
        </div>
      </section>
      <LegalFooter />
    </main>
  );
}
