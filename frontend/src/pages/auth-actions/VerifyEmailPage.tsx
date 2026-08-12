import { useLayoutEffect, useState } from "react";
import { Link } from "react-router-dom";
import { confirmRegistration, getActiveLegalDocuments } from "@/features/auth/api/authApi";
import { ApiError } from "@/features/season/api/apiClient";
import type { LegalDocumentKind, LegalDocumentReadDto } from "@/features/season/api/backendDtos";
import { ROUTES } from "@/shared/constants/routes";
import { Button, KdafikLogo } from "@/shared/ui";

function readTokenFromUrl() {
  return new URL(window.location.href).searchParams.get("token") ?? "";
}

function scrubTokenFromUrl() {
  const url = new URL(window.location.href);
  url.searchParams.delete("token");
  window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}${url.hash}`);
}

const REQUIRED_KINDS: LegalDocumentKind[] = [
  "privacy_policy",
  "personal_data_consent",
  "user_agreement"
];

type LegalChecks = Record<LegalDocumentKind, boolean>;

const EMPTY_CHECKS: LegalChecks = {
  privacy_policy: false,
  personal_data_consent: false,
  user_agreement: false
};

export function VerifyEmailPage() {
  const [token] = useState(readTokenFromUrl);
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [documents, setDocuments] = useState<LegalDocumentReadDto[] | null>(null);
  const [checks, setChecks] = useState<LegalChecks>(EMPTY_CHECKS);
  const [legalLoading, setLegalLoading] = useState(false);

  useLayoutEffect(() => {
    scrubTokenFromUrl();
  }, []);

  async function loadCurrentLegalDocuments() {
    setLegalLoading(true);
    try {
      const currentDocuments = await getActiveLegalDocuments();
      const kinds = new Set(currentDocuments.map((document) => document.kind));
      if (currentDocuments.length !== 3 || REQUIRED_KINDS.some((kind) => !kinds.has(kind))) {
        throw new Error("incomplete legal documents");
      }
      setDocuments(currentDocuments);
      setChecks(EMPTY_CHECKS);
    } catch {
      setErrorMessage("Не удалось загрузить актуальные документы. Повторите попытку позже.");
    } finally {
      setLegalLoading(false);
    }
  }

  async function handleVerify() {
    if (!token) return;
    setStatus("loading");
    setErrorMessage("");
    try {
      await confirmRegistration({
        token,
        legalAcceptances: documents
          ? documents.map((document) => ({
              kind: document.kind,
              version: document.version,
              accepted: checks[document.kind]
            }))
          : undefined
      });
      setStatus("success");
    } catch (error) {
      if (error instanceof ApiError && error.code === "INVALID_LEGAL_ACCEPTANCE") {
        setStatus("idle");
        setErrorMessage("Версии документов обновились. Подтвердите актуальные версии ниже.");
        await loadCurrentLegalDocuments();
        return;
      }
      setErrorMessage(
        error instanceof ApiError && error.code === "RATE_LIMITED"
          ? "Слишком много попыток. Подождите и повторите."
          : "Ссылка недействительна или её срок действия истёк."
      );
      setStatus("error");
    }
  }

  const isLegalAcceptanceIncomplete =
    documents !== null && REQUIRED_KINDS.some((kind) => !checks[kind]);

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
          {!token ? (
            <p className="mt-4 text-sm text-danger">Ссылка не содержит токен подтверждения.</p>
          ) : null}
          {status === "success" ? (
            <div className="mt-6 grid gap-4">
              <p className="text-sm leading-6">
                Почта подтверждена, регистрация завершена. Теперь можно войти.
              </p>
              <Link
                className="w-fit bg-primary px-4 py-2 text-sm font-bold text-primary-foreground"
                to={ROUTES.login}
              >
                Перейти ко входу
              </Link>
            </div>
          ) : (
            <div className="mt-6 grid gap-4">
              <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
                Подтвердите почту вручную. После этого вход потребуется выполнить отдельно.
              </p>
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
                type="button"
                disabled={
                  !token || status === "loading" || legalLoading || isLegalAcceptanceIncomplete
                }
                onClick={() => void handleVerify()}
              >
                {status === "loading"
                  ? "Подтверждаем..."
                  : "Подтвердить почту и завершить регистрацию"}
              </Button>
            </div>
          )}
        </section>
      </section>
    </main>
  );
}
