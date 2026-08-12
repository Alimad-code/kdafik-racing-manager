import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getPublicLegalDocument } from "@/features/auth/api/authApi";
import type {
  LegalDocumentContentReadDto,
  PublicLegalDocumentKind
} from "@/features/season/api/backendDtos";
import { ROUTES } from "@/shared/constants/routes";
import { LegalFooter } from "@/shared/ui";
import { LegalMarkdown } from "./LegalMarkdown";

type LegalDocumentPageProps = { kind: PublicLegalDocumentKind };

export function LegalDocumentPage({ kind }: LegalDocumentPageProps) {
  const [document, setDocument] = useState<LegalDocumentContentReadDto | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    setDocument(null);
    setError(false);
    void getPublicLegalDocument(kind)
      .then((result) => {
        if (active) setDocument(result);
      })
      .catch(() => {
        if (active) setError(true);
      });
    return () => {
      active = false;
    };
  }, [kind]);

  return (
    <main className="flex min-h-screen flex-col text-foreground">
      <section className="mx-auto w-full max-w-4xl flex-1 px-4 py-8 sm:px-6 lg:px-8">
        <Link className="text-sm underline underline-offset-2" to={ROUTES.login}>
          К входу
        </Link>
        {error ? (
          <div className="race-panel mt-5 p-5" role="alert">
            <h1 className="text-xl font-black uppercase">Документ недоступен</h1>
            <p className="mt-3 text-sm text-muted-foreground">
              Текст временно не публикуется: проверьте его целостность и статус утверждения.
            </p>
          </div>
        ) : document ? (
          <article className="race-panel mt-5 p-5 sm:p-7">
            {document.isDraft ? (
              <p className="border border-danger/50 bg-danger/10 p-3 text-xs font-black uppercase tracking-wide text-danger">
                Этот документ не является финальным юридическим текстом.
              </p>
            ) : null}
            <h1 className="mt-5 text-2xl font-black uppercase sm:text-3xl">{document.title}</h1>
            <p className="mt-3 font-mono text-xs text-muted-foreground">
              Версия {document.version} · SHA-256: {document.contentSha256}
            </p>
            <LegalMarkdown content={document.content} />
          </article>
        ) : (
          <p className="mt-5 text-sm text-muted-foreground" role="status">
            Загружаем документ…
          </p>
        )}
      </section>
      <LegalFooter />
    </main>
  );
}
