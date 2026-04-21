import { PropsWithChildren } from "react";
import { Link, NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";

const LANGS = [
  { code: "nl", label: "NL" },
  { code: "en", label: "EN" },
  { code: "tr", label: "TR" },
  { code: "pl", label: "PL" },
  { code: "uk", label: "UK" },
] as const;

const NAV_ITEMS = [
  { to: "/meetings", key: "nav.meetings" },
  { to: "/subscriptions", key: "nav.subscriptions" },
  { to: "/about", key: "nav.about" },
  { to: "/admin", key: "nav.admin" },
] as const;

const AMSTERDAM_LOGO =
  "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4c/Logo_of_Gemeente_Amsterdam.svg/960px-Logo_of_Gemeente_Amsterdam.svg.png";

export function Layout({ children }: PropsWithChildren) {
  const { i18n, t } = useTranslation();

  return (
    <div className="min-h-screen bg-background text-on-surface">
      <header className="sticky top-0 z-20 border-b border-outline-variant/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
        <div className="mx-auto max-w-6xl px-4 md:px-8">
          {/* Top bar: Amsterdam logo + congressmAIn wordmark + lang switcher */}
          <div className="flex h-14 items-center gap-3">
            <img
              src={AMSTERDAM_LOGO}
              alt="Gemeente Amsterdam"
              className="h-8 w-auto object-contain"
              loading="eager"
            />
            <div className="hidden h-5 w-px bg-outline-variant/60 sm:block" />
            <Link
              to="/meetings"
              className="font-serif text-2xl font-bold tracking-tight text-primary hover:opacity-80"
            >
              congressmAIn
            </Link>
            <div className="ml-auto flex items-center gap-1">
              {LANGS.map(({ code, label }) => (
                <button
                  key={code}
                  onClick={() => void i18n.changeLanguage(code)}
                  aria-label={`Switch to ${code.toUpperCase()}`}
                  className={`rounded px-2 py-1 text-xs font-mono transition ${
                    i18n.language === code
                      ? "bg-primary text-white"
                      : "text-on-surface-variant hover:bg-surface-low hover:text-on-surface"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Nav row */}
          <nav className="flex gap-0.5 pb-2 text-sm font-medium">
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `rounded px-3 py-1.5 transition ${
                    isActive
                      ? "bg-primary/10 text-primary font-semibold"
                      : "text-on-surface-variant hover:bg-surface-low hover:text-on-surface"
                  }`
                }
              >
                {t(item.key)}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8 md:px-8">{children}</main>
    </div>
  );
}
