import { useEffect } from "react";
import type { ReactElement } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuthStore } from "@/features/auth/model/useAuthStore";
import { AUTH_EXPIRED_EVENT } from "@/features/auth/model/authSession";
import { useSeasonStore } from "@/features/season/model/useSeasonStore";
import { Button, StatusBadge } from "@/shared/ui";
import { ROUTES } from "@/shared/constants/routes";

type ProtectedRouteProps = {
  children: ReactElement;
};

function ConnectionPanel() {
  const isLoading = useSeasonStore((state) => state.isLoading);
  const errorCode = useSeasonStore((state) => state.errorCode);
  const errorMessage = useSeasonStore((state) => state.errorMessage);
  const bootstrap = useSeasonStore((state) => state.bootstrap);

  function retryBootstrap() {
    void bootstrap().catch(() => undefined);
  }

  if (!errorMessage) {
    return (
      <main className="min-h-screen bg-background" aria-busy="true">
        <span className="sr-only">Восстанавливаем защищённую сессию.</span>
      </main>
    );
  }

  return (
    <main className="grid min-h-screen place-items-center px-6 text-foreground">
      <section className="race-panel w-full max-w-xl p-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="metadata-label">Канал рейс-контроля</p>
            <h1 className="mt-2 text-2xl font-black uppercase">
              {errorMessage ? "Связь прервана" : "Подключение к рейс-контролю"}
            </h1>
          </div>
          <StatusBadge variant={errorMessage ? "danger" : "live"}>
            {errorMessage ? "Ошибка" : "Онлайн"}
          </StatusBadge>
        </div>
        <p className="mt-4 text-sm text-muted-foreground">
          {errorMessage ??
            "Восстанавливаем защищённую сессию, загружаем каталог и синхронизируем активный сезон."}
        </p>
        {errorMessage ? (
          <div className="mt-5 border border-danger/30 bg-danger/10 p-4">
            <p className="metadata-label text-danger">Статус системы</p>
            <p className="mt-2 font-mono text-xs text-foreground">
              {errorCode ?? "CONNECTION_ERROR"}
            </p>
            <Button className="mt-4" type="button" disabled={isLoading} onClick={retryBootstrap}>
              {isLoading ? "Повторяем..." : "Повторить подключение"}
            </Button>
          </div>
        ) : null}
      </section>
    </main>
  );
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const location = useLocation();
  const authStatus = useAuthStore((state) => state.status);
  const markAnonymous = useAuthStore((state) => state.markAnonymous);
  const refresh = useAuthStore((state) => state.refresh);
  const isBootstrapped = useSeasonStore((state) => state.isBootstrapped);
  const isSeasonLoading = useSeasonStore((state) => state.isLoading);
  const bootstrap = useSeasonStore((state) => state.bootstrap);
  const resetSessionState = useSeasonStore((state) => state.resetSessionState);

  useEffect(() => {
    const handleAuthExpired = () => {
      resetSessionState();
      markAnonymous();
    };

    window.addEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);
  }, [markAnonymous, resetSessionState]);

  useEffect(() => {
    if (authStatus === "idle") {
      void refresh();
    }
  }, [authStatus, refresh]);

  useEffect(() => {
    if (authStatus === "authenticated" && !isBootstrapped && !isSeasonLoading) {
      void bootstrap().catch(() => undefined);
    }
  }, [authStatus, bootstrap, isBootstrapped, isSeasonLoading]);

  if (authStatus === "anonymous") {
    return <Navigate to={ROUTES.login} replace state={{ from: location.pathname }} />;
  }

  if (authStatus !== "authenticated" || !isBootstrapped) {
    return <ConnectionPanel />;
  }

  return children;
}
