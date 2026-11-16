import { createFileRoute, Link } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { ArrowDown, LayoutDashboard } from "lucide-react";
import Header from "@/components/Header";
import WhatWeDo from "@/components/WhatWeDo";
import HeroBottle from "@/components/HeroBottle";
import { useLang } from "@/components/LanguageProvider";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "REXO | Your Personal Health Assistant" },
      { name: "description", content: "REXO compares your after-visit summary and clinical note, explains your plan in plain language, and helps you ask your doctor." },
    ],
  }),
  component: HomePage,
});

const RINGS = ["h-[28rem] w-[28rem]", "h-[44rem] w-[44rem]", "h-[60rem] w-[60rem]", "h-[76rem] w-[76rem]"];

function HomePage() {
  const { t } = useLang();
  return (
    <div className="min-h-screen bg-background">
      <Header />
      <section className="relative overflow-hidden bg-primary text-primary-foreground">
        <div className="pointer-events-none absolute -right-40 top-1/2 -translate-y-1/2" aria-hidden="true">
          {RINGS.map((size) => (
            <span key={size} className={`absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full border border-primary-foreground/15 ${size}`} />
          ))}
          <span className="absolute left-1/2 top-1/2 h-48 w-48 -translate-x-1/2 -translate-y-1/2 rounded-full bg-signal-400 blur-2xl" />
        </div>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="relative mx-auto max-w-6xl px-4 pb-20 pt-16 sm:px-6 sm:pb-28 sm:pt-24 lg:grid lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center lg:gap-10"
        >
          <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-primary-foreground/80">
            {t("After your visit", "Después de su visita")}
          </p>
          <h1 className="mt-5 max-w-3xl font-display text-5xl font-normal leading-[1.05] tracking-tight sm:text-7xl">
            {t("Your Personal Health Assistant", "Su asistente personal de salud")}
          </h1>
          <p className="mt-6 max-w-xl text-lg text-primary-foreground/90">
            {t(
              "Bring your after-visit summary and your clinical note. REXO shows your plan in plain words, points out where the two don't match, and helps you ask your doctor.",
              "Traiga su resumen de la visita y su nota clínica. REXO muestra su plan en palabras claras, señala dónde no coinciden y le ayuda a preguntar a su médico."
            )}
          </p>
          <div className="mt-9 flex flex-col gap-3 sm:flex-row">
            <Link to="/dashboard" className="inline-flex h-14 items-center justify-center gap-2 rounded-full bg-background px-7 text-base font-semibold text-foreground transition-transform duration-200 hover:-translate-y-0.5">
              <LayoutDashboard className="h-5 w-5" aria-hidden="true" />
              {t("View patient dashboard", "Ver panel del paciente")}
            </Link>
            <a href="#what-we-do" className="inline-flex h-14 items-center justify-center gap-2 rounded-full border border-primary-foreground/50 px-7 text-base font-semibold transition-colors duration-200 hover:bg-primary-foreground/10">
              {t("What we do", "Qué hacemos")}
              <ArrowDown className="h-5 w-5" aria-hidden="true" />
            </a>
          </div>
          </div>
          <HeroBottle className="hidden h-[26rem] w-auto lg:block" />
        </motion.div>
      </section>
      <WhatWeDo />
    </div>
  );
}