import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import ChatBox from "@/components/ChatBox";
import { useLang } from "@/components/LanguageProvider";

export default function ChatPanel({ open, onOpenChange, ...chat }) {
  const { t } = useLang();
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="flex w-full flex-col gap-0 p-0 sm:max-w-lg">
        <SheetHeader className="border-b border-border p-5 text-left">
          <SheetTitle className="font-display text-3xl font-normal">{t("Let's chat", "Conversemos")}</SheetTitle>
          <SheetDescription>{chat.data?.live
            ? t("Ask about your plan by voice or text. Answers come from your documents first, then trusted drug information and the web, with sources.", "Pregunte sobre su plan por voz o texto. Las respuestas vienen primero de sus documentos, luego de información confiable y de internet, con fuentes.")
            : t("Ask about your plan by voice or text. Demo mode: answers are scripted from sample sources.", "Pregunte sobre su plan por voz o texto. Modo demo: las respuestas vienen de fuentes de ejemplo.")}</SheetDescription>
        </SheetHeader>
        <ChatBox {...chat} />
      </SheetContent>
    </Sheet>
  );
}