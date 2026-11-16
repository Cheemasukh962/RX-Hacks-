import { Link } from "@tanstack/react-router";
import { FlaskConical } from "lucide-react";
import BottleLogo from "@/components/BottleLogo";
import { useLang } from "@/components/LanguageProvider";
import { cn } from "@/lib/utils";

export default function Header() {
  const { lang, setLang, t } = useLang();
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link to="/" className="flex items-center gap-1" aria-label="rexo home">
          <BottleLogo plain />
          <span className="font-display text-3xl font-medium tracking-tight">EXO</span>
        </Link>
        <div className="flex items-center gap-3">
          <Link to="/dashboard" className="inline-flex h-10 items-center px-2 text-sm font-semibold hover:text-signal-600">
            {t("Dashboard", "Panel")}
          </Link>
          <span className="hidden items-center gap-1.5 rounded-full bg-secondary px-3 py-1 text-sm font-medium text-clay sm:inline-flex">
            <FlaskConical className="h-3.5 w-3.5" aria-hidden="true" />
            {t("Demo mode", "Modo demo")}
          </span>
          <div className="flex rounded-full border border-border p-0.5" role="group" aria-label={t("Language", "Idioma")}>
            {["en", "es"].map((code) => (
              <button
                key={code}
                type="button"
                onClick={() => setLang(code)}
                aria-pressed={lang === code}
                className={cn(
                  "h-10 min-w-11 rounded-full px-3 text-sm font-semibold uppercase transition-colors duration-200",
                  lang === code ? "bg-foreground text-background" : "text-muted-foreground hover:text-foreground"
                )}
              >
                {code}
              </button>
            ))}
          </div>
        </div>
      </div>
    </header>
  );
}