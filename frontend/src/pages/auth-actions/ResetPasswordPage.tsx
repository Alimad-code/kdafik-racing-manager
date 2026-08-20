import { useEffect, useState, type FormEvent } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { resendPasswordReset, resetPassword } from "@/features/auth/api/authApi";
import { ApiError } from "@/features/season/api/apiClient";
import { ROUTES } from "@/shared/constants/routes";
import { Button } from "@/shared/ui";

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
  if (!(error instanceof ApiError)) return "Не удалось изменить пароль. Попробуйте ещё раз.";
  if (error.code === "RATE_LIMITED") return "Слишком много попыток. Подождите и повторите.";
  if (error.code === "INVALID_EMAIL_ACTION_CODE")
    return "Код недействителен или срок его действия истёк.";
  return "Не удалось изменить пароль. Попробуйте ещё раз.";
}

export function ResetPasswordPage() {
  const { resetId } = useParams<{ resetId: string }>();
  const location = useLocation();
  const challengeState = readLocationState(location.state);
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [complete, setComplete] = useState(false);
  const [resendLoading, setResendLoading] = useState(false);
  const [resendAvailableAt, setResendAvailableAt] = useState<number | null>(
    challengeState.resendAt
  );
  const [now, setNow] = useState(Date.now());
  const [resendMessage, setResendMessage] = useState("");

  useEffect(() => {
    if (complete || !resendAvailableAt || resendAvailableAt <= now) return;
    const timeout = window.setTimeout(
      () => setNow(Date.now()),
      Math.min(1000, resendAvailableAt - now)
    );
    return () => window.clearTimeout(timeout);
  }, [complete, now, resendAvailableAt]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (!resetId) {
      setError("Операция сброса не найдена. Запросите новый код.");
      return;
    }
    if (!/^\d{6}$/.test(code)) {
      setError("Введите шестизначный код из письма.");
      return;
    }
    if (password.length < 8) {
      setError("Пароль должен быть не короче 8 символов.");
      return;
    }
    if (password !== confirmation) {
      setError("Пароли не совпадают.");
      return;
    }
    setLoading(true);
    try {
      await resetPassword({ resetId, code, newPassword: password });
      setComplete(true);
      setPassword("");
      setConfirmation("");
    } catch (requestError) {
      setError(messageForError(requestError));
    } finally {
      setLoading(false);
    }
  }

  async function handleResend() {
    if (!resetId) return;
    setResendLoading(true);
    setError("");
    try {
      await resendPasswordReset({ resetId });
      const nextAvailableAt = Date.now() + RESEND_COOLDOWN_SECONDS * 1000;
      setResendAvailableAt(nextAvailableAt);
      setResendMessage("Если операция ещё действует, новый код будет отправлен.");
    } catch (requestError) {
      setError(messageForError(requestError));
    } finally {
      setResendLoading(false);
    }
  }

  const resendRemainingSeconds = resendAvailableAt
    ? Math.max(0, Math.ceil((resendAvailableAt - now) / 1000))
    : 0;

  return (
    <main className="grid min-h-screen place-items-center px-4 text-foreground">
      <section className="race-panel w-full max-w-lg p-6">
        <h1 className="text-2xl font-black uppercase">Новый пароль</h1>
        {complete ? (
          <div className="mt-5 grid gap-4">
            <p className="text-sm">Пароль изменён. Войдите с новым паролем.</p>
            <Link
              className="w-fit bg-primary px-4 py-2 text-sm font-bold text-primary-foreground"
              to={ROUTES.login}
            >
              Перейти ко входу
            </Link>
          </div>
        ) : resetId ? (
          <form className="mt-5 grid gap-4" onSubmit={handleSubmit}>
            <p className="text-sm text-muted-foreground">
              {challengeState.maskedEmail
                ? `Введите код, отправленный на ${challengeState.maskedEmail}. Он действует 10 минут.`
                : "Введите код из письма. Он действует 10 минут."}
            </p>
            <label className="grid gap-2" htmlFor="reset-code">
              <span className="metadata-label">Код из письма</span>
              <input
                id="reset-code"
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
            <label className="grid gap-2" htmlFor="reset-password">
              <span className="metadata-label">Новый пароль</span>
              <input
                id="reset-password"
                className="min-h-11 border border-input bg-background px-3"
                type="password"
                autoComplete="new-password"
                minLength={8}
                maxLength={128}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </label>
            <label className="grid gap-2" htmlFor="reset-confirmation">
              <span className="metadata-label">Повторите пароль</span>
              <input
                id="reset-confirmation"
                className="min-h-11 border border-input bg-background px-3"
                type="password"
                autoComplete="new-password"
                minLength={8}
                maxLength={128}
                value={confirmation}
                onChange={(event) => setConfirmation(event.target.value)}
                required
              />
            </label>
            {error ? (
              <p className="text-sm text-danger" role="alert">
                {error}
              </p>
            ) : null}
            <Button type="submit" disabled={loading}>
              {loading ? "Сохраняем..." : "Изменить пароль"}
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
          </form>
        ) : (
          <div className="mt-5 grid gap-4">
            <p className="text-sm text-muted-foreground" role="alert">
              Операция сброса не найдена. Запросите новый код восстановления.
            </p>
            <Link className="w-fit underline" to={ROUTES.forgotPassword}>
              Запросить новый код
            </Link>
          </div>
        )}
      </section>
    </main>
  );
}
