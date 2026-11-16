import { useRef, useState } from "react";
import { useServerFn } from "@tanstack/react-start";
import { Copy, ExternalLink, Loader2, RefreshCw } from "lucide-react";
import { rewriteEmail } from "@/lib/email-fns";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import MicButton from "@/components/MicButton";
import { useLang } from "@/components/LanguageProvider";
import useDictation from "@/hooks/useDictation";
import { DOC_LABELS } from "@/lib/sampleCases";

export default function EmailComposer({ finding, onClose }) {
  const { lang, t } = useLang();
  const [subject, setSubject] = useState(t("Question about my recent visit", "Pregunta sobre mi visita reciente"));
  const [body, setBody] = useState(
    finding
      ? t(`Hello,\n\nI have a question about my recent visit. ${finding.title.en} Can you tell me which one applies to me?`, `Hola,\n\nTengo una pregunta sobre mi visita reciente. ${finding.title.es} ¿Puede decirme cuál aplica a mí?`)
      : t("Hello,\n\nI have a question about my recent visit.", "Hola,\n\nTengo una pregunta sobre mi visita reciente.")
  );
  const [note, setNote] = useState("");
  const [mergedNote, setMergedNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const rewrite = useServerFn(rewriteEmail);
  const baseRef = useRef("");

  const regenerate = async () => {
    setBusy(true);
    setFailed(false);
    try {
      const result = await rewrite({ data: { body, note, topic: finding ? finding.title[lang] : "", lang } });
      if (result.body) {
        setBody(result.body);
        setMergedNote(note);
      } else {
        setFailed(true);
      }
    } catch {
      setFailed(true);
    }
    setBusy(false);
  };
  const dictation = useDictation(lang, (text) => setNote(`${baseRef.current} ${text}`.trim()));
  const mic = { ...dictation, start: () => { baseRef.current = note; dictation.start(); } };

  const quotes = finding ? finding.quotes.map((q) => `${DOC_LABELS[q.doc][lang]}: "${q.quote}"`) : [];
  const full = [body, ...quotes, note && note !== mergedNote && `${t("My note", "Mi nota")}: ${note}`, t("Thank you.", "Gracias.")].filter(Boolean).join("\n\n");

  const copy = async () => {
    await navigator.clipboard.writeText(`${subject}\n\n${full}`);
    toast.success(t("Copied", "Copiado"));
  };

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[92vh] overflow-y-auto sm:max-w-xl">
        <DialogHeader className="text-left">
          <DialogTitle className="font-display text-3xl font-normal">{t("Email my doctor", "Escribir a mi médico")}</DialogTitle>
          <DialogDescription>{t("Edit anything. REXO never sends email. It opens in your own email app.", "Edite lo que quiera. REXO nunca envía correos. Se abre en su propia app de correo.")}</DialogDescription>
        </DialogHeader>
        <label className="block text-sm font-semibold">
          {t("Subject", "Asunto")}
          <Input value={subject} onChange={(e) => setSubject(e.target.value)} className="mt-1 h-12 text-base" />
        </label>
        <label className="block text-sm font-semibold">
          {t("Message", "Mensaje")}
          <Textarea value={body} onChange={(e) => setBody(e.target.value)} rows={6} className="mt-1 text-base" />
        </label>
        {quotes.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-semibold">{t("Quotes from your documents (added for you)", "Citas de sus documentos (añadidas por usted)")}</p>
            {quotes.map((q) => <blockquote key={q} className="border-l-2 border-caution bg-caution-soft px-3 py-2 font-display italic">{q}</blockquote>)}
          </div>
        )}
        <div>
          <label className="block text-sm font-semibold">
            {t("Your note", "Su nota")}
            <Textarea value={note} onChange={(e) => setNote(e.target.value)} rows={3} placeholder={t("Say or type what you want to add", "Diga o escriba lo que quiera añadir")} className="mt-1 text-base" />
          </label>
          <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
            <MicButton dictation={mic} />
            <button type="button" onClick={regenerate} disabled={busy || !note.trim()} className="inline-flex h-11 items-center gap-2 rounded-full border border-foreground px-5 text-base font-semibold transition-colors duration-200 hover:bg-foreground hover:text-background disabled:border-border disabled:text-stone disabled:hover:bg-transparent disabled:hover:text-stone">
              {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <RefreshCw className="h-4 w-4" aria-hidden="true" />}
              {busy ? t("Rewriting…", "Reescribiendo…") : t("Regenerate", "Regenerar")}
            </button>
          </div>
          <p className="mt-2 text-sm text-stone" role="status">
            {failed
              ? t("I couldn't rewrite it safely. Your message is unchanged.", "No pude reescribirlo de forma segura. Su mensaje no cambió.")
              : t("Regenerate rewrites your message using your note. The quotes stay exactly as written.", "Regenerar reescribe su mensaje usando su nota. Las citas quedan tal como están.")}
          </p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          <a href={`mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(full)}`} className="inline-flex h-12 flex-1 items-center justify-center gap-2 rounded-full bg-primary px-6 text-base font-semibold text-primary-foreground hover:bg-signal-600">
            <ExternalLink className="h-5 w-5" aria-hidden="true" />
            {t("Open in email app", "Abrir en la app de correo")}
          </a>
          <button type="button" onClick={copy} className="inline-flex h-12 items-center justify-center gap-2 rounded-full border border-foreground px-6 text-base font-semibold">
            <Copy className="h-5 w-5" aria-hidden="true" />
            {t("Copy", "Copiar")}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}