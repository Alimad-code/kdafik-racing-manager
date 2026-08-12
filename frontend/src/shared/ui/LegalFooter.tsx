import { Link } from "react-router-dom";
import { ROUTES } from "@/shared/constants/routes";

export function LegalFooter() {
  return (
    <footer className="border-t border-border/80 px-3 py-3 text-center text-[10px] font-medium uppercase tracking-[0.12em] text-muted-foreground sm:px-5 lg:px-8">
      <div className="flex flex-wrap items-center justify-center gap-x-3 gap-y-1">
        <span>KDAFIK RACING MANAGER</span>
        <Link
          className="underline underline-offset-2 hover:text-foreground"
          to={ROUTES.legalPrivacy}
        >
          Политика данных
        </Link>
        <Link
          className="underline underline-offset-2 hover:text-foreground"
          to={ROUTES.legalConsent}
        >
          Согласие на данные
        </Link>
        <Link
          className="underline underline-offset-2 hover:text-foreground"
          to={ROUTES.legalAgreement}
        >
          Соглашение
        </Link>
        <Link
          className="underline underline-offset-2 hover:text-foreground"
          to={ROUTES.legalCookies}
        >
          Cookie и хранилище
        </Link>
      </div>
    </footer>
  );
}
