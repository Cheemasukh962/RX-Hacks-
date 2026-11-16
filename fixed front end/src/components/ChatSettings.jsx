import { Settings } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Switch } from "@/components/ui/switch";
import { useLang } from "@/components/LanguageProvider";

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