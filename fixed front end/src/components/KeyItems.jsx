import { useState } from "react";
import { CalendarCheck, Pill, Siren } from "lucide-react";
import KeyItemCard from "@/components/KeyItemCard";
import { useLang } from "@/components/LanguageProvider";
import { cn } from "@/lib/utils";

export const GROUPS = [
  { id: "meds", kinds: ["medication"], icon: Pill, title: { en: "Medications", es: "Medicamentos" } },
  { id: "tasks", kinds: ["follow_up", "lab", "lifestyle", "supply"], icon: CalendarCheck, title: { en: "Follow-ups & tasks", es: "Seguimiento y tareas" } },
  { id: "warnings", kinds: ["warning_sign"], icon: Siren, title: { en: "Warning signs", es: "Señales de alerta" } },
];

export default function KeyItems({ data, altered, onWhy }) {
  const { lang, t } = useLang();
  const [filter, setFilter] = useState("all");
  const all = GROUPS.flatMap((group) =>
    data.instructions.filter((i) => group.kinds.includes(i.kind)).map((item) => ({ item, group }))
  );
  const shown = all.filter(({ group }) => filter === "all" || group.id === filter);
  const filters = [
    { id: "all", label: t("All", "Todo"), count: all.length },
    ...GROUPS.map((g) => ({ id: g.id, label: g.title[lang], count: all.filter((x) => x.group.id === g.id).length })),
  ];

  return (
    <div>
      <div className="flex flex-wrap gap-2" role="group" aria-label={t("Filter key items", "Filtrar puntos clave")}>
        {filters.map((f) => (
          <button
            key={f.id}
            type="button"
            aria-pressed={filter === f.id}
            onClick={() => setFilter(f.id)}
            className={cn(
              "inline-flex h-11 items-center gap-2 rounded-full border px-5 text-base font-semibold transition-colors duration-200",
              filter === f.id ? "border-foreground bg-foreground text-background" : "border-border bg-card hover:border-foreground"
            )}
          >
            {f.label}
            <span className={filter === f.id ? "text-sm font-medium opacity-70" : "text-sm font-medium text-stone"}>{f.count}</span>
          </button>
        ))}
      </div>
      {shown.length ? (
        <div className="mt-6 grid items-start gap-4 md:grid-cols-2 lg:grid-cols-3">
          {shown.map(({ item, group }) => (
            <KeyItemCard key={item.id} item={item} group={group} disputed={item.disputed || (altered && item.disputedWhenAltered)} onWhy={item.hasRisk && onWhy ? onWhy : null} />
          ))}
        </div>
      ) : (
        <p className="mt-6 rounded-2xl border border-border bg-card p-6 italic text-stone">{t("Not in your documents", "No está en sus documentos")}</p>
      )}
    </div>
  );
}