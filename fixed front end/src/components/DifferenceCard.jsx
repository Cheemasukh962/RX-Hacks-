import { motion, useReducedMotion } from "framer-motion";
import { AlertTriangle, Info, Mail, Phone } from "lucide-react";
import QuoteCard from "@/components/QuoteCard";
import { Button } from "@/components/ui/button";
import { useLang } from "@/components/LanguageProvider";

const KIND = {
  within_document: { en: "One document says two things", es: "Un documento dice dos cosas" },
  only_in_one: { en: "Only in one document", es: "Solo en un documento" },
  worded_differently: { en: "Worded differently, ask your care team", es: "Redactado distinto, pregunte a su equipo" },
};
const MISMATCH = { en: "Your documents don't match", es: "Sus documentos no coinciden" };

export default function DifferenceCard({ finding, onEmail, onCall }) {
  const { lang, t } = useLang();
  const reduce = useReducedMotion();
  const info = finding.type === "only_in_one";
  const Icon = info ? Info : AlertTriangle;
  const pair = finding.quotes.length === 2;

  return (
    <article className={info ? "rounded-2xl bg-clinical-50 p-5 sm:p-7" : "rounded-2xl bg-caution-soft p-5 sm:p-7"}>
      <p className={info ? "flex items-center gap-2 text-sm font-semibold text-clinical" : "flex items-center gap-2 text-sm font-semibold text-caution"}>
        <Icon className="h-4 w-4" aria-hidden="true" />
        {(KIND[finding.type] || MISMATCH)[lang]}
        {!info && <span className="font-normal">· {t("Needs clarification", "Necesita aclaración")}</span>}
      </p>
      <h3 className="mt-2 text-xl font-semibold leading-snug">{finding.title[lang]}</h3>
      <div className={pair ? "mt-5 grid gap-3 sm:grid-cols-2" : "mt-5"}>
        {finding.quotes.map((q, i) => (
          <motion.div
            key={i}
            initial={reduce || !pair ? false : { x: i === 0 ? "22%" : "-22%", opacity: 0.5 }}
            whileInView={{ x: 0, opacity: 1 }}
            viewport={{ once: true, amount: 0.6 }}
            transition={{ duration: 0.55, ease: "easeOut" }}
          >
            <QuoteCard evidence={q} />
          </motion.div>
        ))}
      </div>
      <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center">
        <Button onClick={() => onEmail(finding)} className="h-12 rounded-full px-6 text-base">
          <Mail className="h-5 w-5" aria-hidden="true" />
          {t("Email my doctor", "Escribir a mi médico")}
        </Button>
        <Button variant="outline" onClick={() => onCall(finding)} className="h-12 rounded-full border-foreground bg-transparent px-6 text-base">
          <Phone className="h-5 w-5" aria-hidden="true" />
          {t("Call my doctor", "Llamar a mi médico")}
        </Button>
        <p className="text-sm text-stone">{t("Your doctor decides which applies. You decide what to send.", "Su médico decide cuál aplica. Usted decide qué enviar.")}</p>
      </div>
    </article>
  );
}