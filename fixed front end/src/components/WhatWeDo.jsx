import { AlertTriangle, FileSearch, Mail, MessageCircle, Quote } from "lucide-react";
import { useLang } from "@/components/LanguageProvider";

const ITEMS = [
  {
    icon: FileSearch,
    title: { en: "Your plan in plain words", es: "Su plan en palabras claras" },
    text: { en: "We read your after-visit summary and clinical note and list your medicines, follow-ups and warning signs.", es: "Leemos su resumen de la visita y su nota clínica y listamos sus medicamentos, seguimientos y señales de alerta." },
  },
  {
    icon: AlertTriangle,
    title: { en: "Differences flagged", es: "Diferencias señaladas" },
    text: { en: "When your two documents don't match, you see both quotes side by side.", es: "Cuando sus dos documentos no coinciden, ve ambas citas lado a lado." },
  },
  {
    icon: MessageCircle,
    title: { en: "Answers with sources", es: "Respuestas con fuentes" },
    text: { en: "Ask a question by typing or speaking. Every answer points to the words in your documents.", es: "Pregunte escribiendo o hablando. Cada respuesta señala las palabras de sus documentos." },
  },
  {
    icon: Mail,
    title: { en: "Help asking your doctor", es: "Ayuda para preguntar a su médico" },
    text: { en: "We draft an email you can edit. You decide what to send.", es: "Redactamos un correo que puede editar. Usted decide qué enviar." },
  },
];

export default function WhatWeDo() {
  const { lang, t } = useLang();
  return (
    <section id="what-we-do" className="mx-auto max-w-6xl scroll-mt-16 px-4 py-16 sm:px-6 sm:py-24">
      <p className="text-sm font-semibold uppercase tracking-[0.18em] text-stone">{t("What we do", "Qué hacemos")}</p>
      <h2 className="mt-4 max-w-2xl font-display text-4xl font-normal leading-[1.1] tracking-tight">
        {t("We help you understand your care after a visit.", "Le ayudamos a entender su atención después de una visita.")}
      </h2>
      <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {ITEMS.map((item) => (
          <article key={item.title.en} className="rounded-2xl border border-border bg-card p-6">
            <span className="flex h-11 w-11 items-center justify-center rounded-full bg-blush text-signal-600">
              <item.icon className="h-5 w-5" aria-hidden="true" />
            </span>
            <h3 className="mt-5 text-xl font-semibold leading-snug">{item.title[lang]}</h3>
            <p className="mt-2 text-muted-foreground">{item.text[lang]}</p>
          </article>
        ))}
      </div>
      <div className="mt-10 flex items-start gap-4 rounded-2xl bg-blush p-6 sm:p-8">
        <Quote className="mt-1 h-6 w-6 shrink-0 text-signal-600" aria-hidden="true" />
        <p className="text-lg">
          {t(
            "Every fact REXO shows sits next to the exact words from your documents. When the documents disagree, you see both. Your doctor decides which applies.",
            "Cada dato que REXO muestra aparece junto a las palabras exactas de sus documentos. Cuando no coinciden, usted ve ambos. Su médico decide cuál aplica."
          )}
        </p>
      </div>
    </section>
  );
}