import { useEffect, useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import {
  confirmRegistration,
  getActiveLegalDocuments,
  resendVerification
} from "@/features/auth/api/authApi";
import { ApiError } from "@/features/season/api/apiClient";
import type { LegalDocumentKind, LegalDocumentReadDto } from "@/features/season/api/backendDtos";
import { ROUTES } from "@/shared/constants/routes";
import { Button, KdafikLogo } from "@/shared/ui";

const REQUIRED_KINDS: LegalDocumentKind[] = [
  "privacy_policy",
  "personal_data_consent",
  "user_agreement"
];
const EMPTY_CHECKS: Record<LegalDocumentKind, boolean> = {
  privacy_policy: false,
  personal_data_consent: false,
  user_agreement: false
};
const RESEND_COOLDOWN_SECONDS = 60;

function readLocationState(state: unknown) {
  if (typeof state !== "object" || state === null) return { maskedEmail: "", resendAt: null };
  const candidate = state as Record<string, unknown>;
  return {
    maskedEmail: typeof candidate.maskedEmail === "string" ? candidate.maskedEmail : "",
    resendAt: typeof candidate.resendAvailableAt === "number" ? candidate.resendAvailableAt : null
  };
}

function messageForError(error: unknown) {
  if (!(error instanceof ApiError)) return "Не удалось подтвердить email. Повторите попытку.";
  if (error.code === "RATE_LIMITED") return "Слишком много попыток. Подождите и повторите.";
  if (error.code === "INVALID_EMAIL_ACTION_CODE")
    return "Код недействителен или срок его действия истёк.";
  return "Не удалось подтвердить email. Повторите попытку.";
}

export function VerifyEmailPage() {
  const { confirmationId } = useParams<{ confirmationId: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const challengeState = readLocationState(location.state);
  const [code, setCode] = useState("");
  const [status, setStatus] = useState<"idle" | "loading">("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [documents, setDocuments] = useState<LegalDocumentReadDto[] | null>(null);
  const [checks, setChecks] = useState(EMPTY_CHECKS);
  const [legalLoading, setLegalLoading] = useState(false);
  const [resendLoading, setResendLoading] = useState(false);
  const [resendAvailableAt, setResendAvailableAt] = useState<number | null>(
    challengeState.resendAt
  );
  const [now, setNow] = useState(Date.now());
  const [resendMessage, setResendMessage] = useState("");

  useEffect(() => {
    if (!resendAvailableAt || resendAvailableAt <= now) return;
    const timeout = window.setTimeout(
      () => setNow(Date.now()),
      Math.min(1000, resendAvailableAt - now)
    );
    return () => window.clearTimeout(timeout);
  }, [now, resendAvailableAt]);

  async function loadCurrentLegalDocuments() {
    setLegalLoading(true);
    try {
      const currentDocuments = await getActiveLegalDocuments();
      const kinds = new Set(currentDocuments.map((document) => document.kind));
      if (currentDocuments.length !== 3 || REQUIRED_KINDS.some((kind) => !kinds.has(kind)))
        throw new Error("incomplete legal documents");
      setDocuments(currentDocuments);
      setChecks(EMPTY_CHECKS);
    } catch {
      setErrorMessage("Не удалось загрузить актуальные документы. Повторите попытку позже.");
    } finally {
      setLegalLoading(false);
    }
  }

  async function handleVerify(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!confirmationId) {
      setErrorMessage("Операция подтверждения не найдена. Начните регистрацию заново.");
      return;
    }
    if (!/^\d{6}$/.test(code)) {
      setErrorMessage("Введите шестизначный код из письма.");
      return;
    }
    if (documents && REQUIRED_KINDS.some((kind) => !checks[kind])) {
      setErrorMessage("Подтвердите каждый актуальный документ.");
      return;
    }
    setStatus("loading");
    setErrorMessage("");
    try {
      await confirmRegistration({
        confirmationId,
        code,
        legalAcceptances: documents
          ? documents.map((document) => ({
              kind: document.kind,
              version: document.version,
              accepted: checks[document.kind]
            }))
          : undefined
      });
      navigate(ROUTES.login, { replace: true });
    } catch (error) {
      if (error instanceof ApiError && error.code === "INVALID_LEGAL_ACCEPTANCE") {
        setErrorMessage("Версии документов обновились. Подтвердите актуальные версии ниже.");
        await loadCurrentLegalDocuments();
      } else setErrorMessage(messageForError(error));
    } finally {
      setStatus("idle");
    }
  }

  async function handleResend() {
    if (!confirmationId) return;
    setResendLoading(true);
    setErrorMessage("");
    try {
      await resendVerification({ confirmationId });
      setResendAvailableAt(Date.now() + RESEND_COOLDOWN_SECONDS * 1000);
      setResendMessage("Новый код отправлен на адрес регистрации.");
    } catch (error) {
      setErrorMessage(messageForError(error));
    } finally {
      setResendLoading(false);
    }
  }

  const resendRemainingSeconds = resendAvailableAt
    ? Math.max(0, Math.ceil((resendAvailableAt - now) / 1000))
    : 0;
  const legalIncomplete = documents !== null && REQUIRED_KINDS.some((kind) => !checks[kind]);

  return (
    <main className="flex min-h-screen flex-col text-foreground">
      <section className="flex flex-1 items-center justify-center px-3 py-5 sm:px-6 sm:py-8">
        <section className="race-panel w-full max-w-xl p-5 sm:p-8">
          <div className="flex items-center gap-3 text-primary">
            <KdafikLogo className="h-6 w-24 shrink-0" />
            <span className="text-[11px] font-black uppercase tracking-[0.2em] sm:text-xs sm:tracking-[0.28em]">
              Kdafik Racing Manager
            </span>
          </div>
          <div className="mt-7">
            <p className="metadata-label">Регистрация профиля</p>
            <h1 className="mt-2 text-3xl font-black uppercase leading-none tracking-tight sm:text-4xl">
              Подтверждение email
            </h1>
          </div>
          {confirmationId ? (
            <form className="mt-6 grid gap-4" onSubmit={handleVerify}>
              <p className="text-sm leading-6 text-muted-foreground">
                {challengeState.maskedEmail
                  ? `Код отправлен на ${challengeState.maskedEmail}. Он действует 15 минут.`
                  : "Введите код, отправленный на адрес регистрации. Он действует 15 минут."}
              </p>
              <label className="grid gap-2" htmlFor="verification-code">
                <span className="metadata-label">Код из письма</span>
                <input
                  id="verification-code"
                  className="min-h-12 border border-input bg-background px-3 text-center font-mono text-xl font-bold tracking-[0.08em]"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  pattern="[0-9]{6}"
                  maxLength={6}
                  value={code}
                  onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
                  required
                />
              </label>
              {errorMessage ? (
                <p className="text-sm text-danger" role="alert">
                  {errorMessage}
                </p>
              ) : null}
              {documents ? (
                <fieldset className="grid gap-3 border border-border p-3" disabled={legalLoading}>
                  <legend className="px-1 text-sm font-bold">Актуальные документы</legend>
                  {documents.map((document) => (
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
              <Button
                className="w-full whitespace-normal px-4 py-3 text-center leading-tight"
                type="submit"
                disabled={status === "loading" || legalLoading || legalIncomplete}
              >
                {status === "loading"
                  ? "Подтверждаем..."
                  : "Подтвердить почту и завершить регистрацию"}
              </Button>
              <Button
                type="button"
                variant="secondary"
                disabled={resendLoading || resendRemainingSeconds > 0}
                onClick={() => void handleResend()}
              >
                {resendLoading
                  ? "Отправляем..."
                  : resendRemainingSeconds > 0
                    ? `Повторная отправка через ${resendRemainingSeconds} с`
                    : "Отправить код повторно"}
              </Button>
              {resendMessage ? (
                <p className="text-sm text-muted-foreground" role="status">
                  {resendMessage}
                </p>
              ) : null}
              <p className="text-sm text-muted-foreground">
                Ошиблись в адресе?{" "}
                <Link className="underline" to={ROUTES.login}>
                  Начните регистрацию заново
                </Link>
                .
              </p>
            </form>
          ) : (
            <div className="mt-6 grid gap-4">
              <p className="text-sm text-muted-foreground" role="alert">
                Операция подтверждения не найдена. Начните регистрацию заново, чтобы получить код.
              </p>
              <Link className="w-fit underline" to={ROUTES.login}>
                Вернуться к регистрации
              </Link>
            </div>
          )}
        </section>
      </section>
    </main>
  );
}
