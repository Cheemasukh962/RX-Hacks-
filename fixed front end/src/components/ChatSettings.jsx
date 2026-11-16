import { Settings } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Switch } from "@/components/ui/switch";
import { useLang } from "@/components/LanguageProvider";
import { cn } from "@/lib/utils";

export default function ChatSettings({ settings, onChange }) {
  const { t } = useLang();
  const options = [
    ["autoRead", t("Read answers aloud", "Leer las respuestas en voz alta")],
    ["largeText", t("Larger text", "Texto más grande")],
  ];
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button type="button" aria-label={t("Chat settings", "Ajustes del chat")} className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full border border-input bg-card">
          <Settings className="h-5 w-5" aria-hidden="true" />
        </button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-72 space-y-4">
        <p className="font-semibold">{t("Chat settings", "Ajustes del chat")}</p>
        <div>
          <p className="text-base">{t("Talk to me", "Hábleme")}</p>
          <div className="mt-2 grid grid-cols-3 gap-1 rounded-full border border-border p-0.5" role="group" aria-label={t("How REXO talks to you", "Cómo le habla REXO")}>
            {[["simple", t("Simple", "Simple")], ["normal", t("Normal", "Normal")], ["detailed", t("Detailed", "Detallado")]].map(([value, label]) => (
              <button key={value} type="button" aria-pressed={(settings.level || "normal") === value} onClick={() => onChange({ ...settings, level: value })}
                className={cn("h-10 rounded-full text-sm font-semibold transition-colors duration-200", (settings.level || "normal") === value ? "bg-foreground text-background" : "text-stone")}>
                {label}
              </button>
            ))}
          </div>
        </div>
        {options.map(([key, label]) => (
          <label key={key} className="flex min-h-11 items-center justify-between gap-4 text-base">
            {label}
            <Switch checked={settings[key]} onCheckedChange={(value) => onChange({ ...settings, [key]: value })} />
          </label>
        ))}
      </PopoverContent>
    </Popover>
  );
}