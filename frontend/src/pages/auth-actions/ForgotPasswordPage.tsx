import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { forgotPassword } from "@/features/auth/api/authApi";
import { ROUTES } from "@/shared/constants/routes";
import { Button } from "@/shared/ui";

export function ForgotPasswordPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const response = await forgotPassword({ email: email.trim() });
      navigate(`${ROUTES.resetPassword}/${response.resetId}`, {
        state: {
          maskedEmail: response.maskedEmail,
          resendAvailableAt: Date.now() + 60_000
        }
      });
    } catch {
      setError("Не удалось отправить код. Попробуйте ещё раз позже.");
    } finally {
      setLoading(false);
    }
  }
  return (
    <main className="grid min-h-screen place-items-center px-4 text-foreground">
      <section className="race-panel w-full max-w-lg p-6">
        <h1 className="text-2xl font-black uppercase">Восстановление пароля</h1>
        <p className="mt-3 text-sm text-muted-foreground">Укажите email профиля.</p>
        <form className="mt-5 grid gap-4" onSubmit={handleSubmit}>
          <label className="grid gap-2" htmlFor="forgot-email">
            <span className="metadata-label">Email</span>
            <input
              id="forgot-email"
              className="min-h-11 border border-input bg-background px-3"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>
          {error ? (
            <p className="text-sm text-danger" role="alert">
              {error}
            </p>
          ) : null}
          <Button type="submit" disabled={loading}>
            {loading ? "Отправляем..." : "Отправить код"}
          </Button>
        </form>
        <Link className="mt-5 inline-block text-sm underline" to={ROUTES.login}>
          Вернуться ко входу
        </Link>
      </section>
    </main>
  );
}
