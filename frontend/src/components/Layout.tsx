import { PropsWithChildren } from "react";
import { Link, NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";

const LANGS = ["nl", "en", "tr", "pl", "uk"] as const;

export function Layout({ children }: PropsWithChildren) {
  const { i18n, t } = useTranslation();

  return (
    <div className="min-h-screen bg-background text-on-surface">
      <header className="sticky top-0 z-20 border-b border-outline-variant/40 bg-background/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 md:px-8">
          <div className="flex items-center gap-8">
            <Link to="/meetings" className="font-serif text-3xl font-bold tracking-tight text-primary">
              AI020
            </Link>
            <nav className="hidden gap-6 text-sm font-medium md:flex">
              <NavLink to="/meetings">{t("nav.meetings")}</NavLink>
              <NavLink to="/subscriptions">{t("nav.subscriptions")}</NavLink>
              <NavLink to="/about">{t("nav.about")}</NavLink>
              <NavLink to="/admin">{t("nav.admin")}</NavLink>
            </nav>
          </div>
          <div className="flex gap-2">
            {LANGS.map((language) => (
              <button
                key={language}
                onClick={() => void i18n.changeLanguage(language)}
                className={`rounded border px-2 py-1 text-xs font-mono uppercase ${
                  i18n.language === language
                    ? "border-primary bg-primary text-white"
                    : "border-outline-variant bg-surface-lowest text-on-surface-variant"
                }`}
              >
                {language}
              </button>
            ))}
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8 md:px-8">{children}</main>
    </div>
  );
}
