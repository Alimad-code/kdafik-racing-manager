import { useLayoutEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { resetPassword } from "@/features/auth/api/authApi";
import { ApiError } from "@/features/season/api/apiClient";
import { ROUTES } from "@/shared/constants/routes";
import { Button } from "@/shared/ui";

function readResetTokenFromUrl() {
  return new URL(window.location.href).searchParams.get("token") ?? "";
}

function scrubResetTokenFromUrl() {
  const url = new URL(window.location.href);
  url.searchParams.delete("token");
  window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}${url.hash}`);
}

export function ResetPasswordPage() {
  const [token] = useState(readResetTokenFromUrl);
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [complete, setComplete] = useState(false);

  useLayoutEffect(() => {
    scrubResetTokenFromUrl();
  }, []);
  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (!token) {
      setError("Ссылка не содержит токен восстановления.");
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
      await resetPassword({ token, newPassword: password });
      setComplete(true);
      setPassword("");
      setConfirmation("");
    } catch (requestError) {
      setError(
        requestError instanceof ApiError && requestError.code === "RATE_LIMITED"
          ? "Слишком много попыток. Подождите и повторите."
          : requestError instanceof ApiError && requestError.code === "INVALID_EMAIL_ACTION_TOKEN"
            ? "Ссылка недействительна или её срок действия истёк."
            : "Не удалось изменить пароль. Попробуйте ещё раз."
      );
    } finally {
      setLoading(false);
    }
  }
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
        ) : (
          <form className="mt-5 grid gap-4" onSubmit={handleSubmit}>
            <label className="grid gap-2" htmlFor="reset-password">
              <span className="metadata-label">Новый пароль</span>
              <input
                id="reset-password"
                className="min-h-11 border border-input bg-background px-3"
                type="password"
                autoComplete="new-password"
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
            <Button type="submit" disabled={!token || loading}>
              {loading ? "Сохраняем..." : "Изменить пароль"}
            </Button>
          </form>
        )}
      </section>
    </main>
  );
}
