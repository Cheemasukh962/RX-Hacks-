import { motion } from "framer-motion";
import { Mic, Square } from "lucide-react";
import { useLang } from "@/components/LanguageProvider";
import { cn } from "@/lib/utils";

export default function MicButton({ dictation, large }) {
  const { t } = useLang();
  const { listening, blocked, busy, error, start, stop } = dictation;
  return (
    <div className="flex items-center gap-3">
      <button
        type="button"
        onClick={listening ? stop : start}
        disabled={busy}
        aria-label={listening ? t("Stop listening", "Dejar de escuchar") : t("Speak", "Hablar")}
        className={cn(
          "flex shrink-0 items-center justify-center rounded-full transition-colors duration-200",
          large ? "h-14 w-14" : "h-11 w-11",
          listening ? "bg-foreground text-background" : "bg-primary text-primary-foreground hover:bg-signal-600"
        )}
      >
        {listening ? <Square className="h-5 w-5" aria-hidden="true" /> : <Mic className="h-6 w-6" aria-hidden="true" />}
      </button>
      {listening && (
        <div className="flex items-center gap-2 text-sm font-medium text-clinical" role="status">
          <span className="flex h-5 items-center gap-0.5" aria-hidden="true">
            {[0, 1, 2, 3].map((i) => (
              <motion.span key={i} className="w-1 rounded-full bg-clinical" animate={{ height: [6, 18, 6] }} transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.12 }} />
            ))}
          </span>
          {t("Listening…", "Escuchando…")}
        </div>
      )}
      {busy && <p role="status" className="text-sm font-medium text-clinical">{t("Transcribing…", "Transcribiendo…")}</p>}
      {error && !busy && !listening && <p role="alert" className="text-sm text-muted-foreground">{error}</p>}
      {blocked && !listening && <p className="text-sm text-muted-foreground">{t("You can type instead.", "Puede escribir en su lugar.")}</p>}
    </div>
  );
}