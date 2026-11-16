import { useState } from "react";
import { FileUp } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import { useLang } from "@/components/LanguageProvider";

export default function DocumentSlot({ label, value, onChange }) {
  const { t } = useLang();
  const [pdfName, setPdfName] = useState("");

  const onFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.name.toLowerCase().endsWith(".pdf")) return setPdfName(file.name);
    setPdfName("");
    onChange(await file.text());
  };

  return (
    <section className="rounded-2xl border border-dashed border-input bg-card p-5 sm:p-6">
      <h2 className="text-xl font-semibold">{label}</h2>
      <label className="mt-4 flex min-h-24 cursor-pointer flex-col items-center justify-center gap-2 rounded-xl bg-blush p-4 text-center font-semibold transition-colors duration-200 hover:bg-secondary">
        <FileUp className="h-6 w-6 text-signal-600" aria-hidden="true" />
        {t("Choose a PDF or text file", "Elija un PDF o archivo de texto")}
        <input type="file" accept=".pdf,.txt" onChange={onFile} className="sr-only" />
      </label>
      {pdfName && (
        <p className="mt-3 rounded-xl bg-secondary px-4 py-3 text-sm text-clay">
          {pdfName}: {t("PDF reading isn't connected in demo mode. Paste the text instead.", "La lectura de PDF no está conectada en modo demo. Pegue el texto.")}
        </p>
      )}
      <label className="mt-4 block text-sm font-semibold">
        {t("Or paste the text", "O pegue el texto")}
        <Textarea value={value} onChange={(e) => onChange(e.target.value)} rows={7} className="mt-1 text-base" />
      </label>
    </section>
  );
}