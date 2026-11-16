import { MotionConfig, motion } from "framer-motion";
import { cn } from "@/lib/utils";

const MOUTH = { x: 165, y: 172 };
const PILLS = [
  { x: 70, y: 112, rot: -35 }, { x: 122, y: 62, rot: 20 }, { x: 178, y: 30, rot: -15 }, { x: 240, y: 66, rot: 40 },
  { x: 278, y: 128, rot: -25 }, { x: 150, y: 118, rot: 60 }, { x: 214, y: 124, rot: -50 },
  { x: 96, y: 160, r: 11 }, { x: 40, y: 150, r: 9 }, { x: 204, y: 76, r: 10 }, { x: 262, y: 176, r: 9 },
  { x: 104, y: 20, r: 9 }, { x: 290, y: 52, r: 11 }, { x: 34, y: 64, r: 10 },
];

function Pill({ pill }) {
  if (pill.r) {
    return (
      <>
        <circle r={pill.r} className="fill-background" />
        <line x1={-pill.r * 0.55} x2={pill.r * 0.55} strokeWidth="2" strokeLinecap="round" className="stroke-sand" />
      </>
    );
  }
  return (
    <g transform={`rotate(${pill.rot})`}>
      <rect x="-22" y="-9" width="44" height="18" rx="9" className="fill-background" />
      <path d="M0 -9 H13 a9 9 0 0 1 0 18 H0 Z" className="fill-foreground" />
    </g>
  );
}

// Home hero picture: the bottle's cap swings open and a bunch of pills pop out, then drift.
export default function HeroBottle({ className }) {
  return (
    <MotionConfig reducedMotion="user">
      <svg viewBox="0 0 320 390" className={cn("overflow-visible", className)} aria-hidden="true">
        <ellipse cx="165" cy="376" rx="86" ry="9" className="fill-signal-800/60" />
        {PILLS.map((pill, i) => (
          <g key={i} transform={`translate(${pill.x} ${pill.y})`}>
            <motion.g
              initial={{ x: MOUTH.x - pill.x, y: MOUTH.y - pill.y, scale: 0, opacity: 0 }}
              animate={{ x: 0, y: 0, scale: 1, opacity: 1 }}
              transition={{ type: "spring", stiffness: 90, damping: 12, delay: 0.5 + i * 0.05 }}
            >
              <motion.g animate={{ y: [0, -7, 0] }} transition={{ duration: 3 + (i % 3) * 0.6, repeat: Infinity, ease: "easeInOut", delay: i * 0.2 }}>
                <Pill pill={pill} />
              </motion.g>
            </motion.g>
          </g>
        ))}
        <rect x="122" y="170" width="86" height="24" rx="4" className="fill-secondary" />
        <rect x="108" y="190" width="114" height="182" rx="14" className="fill-background" />
        <rect x="108" y="238" width="114" height="78" className="fill-blush" />
        <text x="165" y="287" textAnchor="middle" fontSize="28" className="fill-primary font-display font-semibold">REXO</text>
        <motion.g
          style={{ originX: 1, originY: 1 }}
          initial={{ rotate: 0, y: 0 }}
          animate={{ rotate: 48, y: -6 }}
          transition={{ duration: 0.6, ease: "easeOut", delay: 0.2 }}
        >
          <rect x="112" y="142" width="106" height="30" rx="6" className="fill-foreground" />
          {[132, 148, 164, 180, 196].map((x) => (
            <line key={x} x1={x} x2={x} y1="149" y2="165" strokeWidth="3" strokeLinecap="round" className="stroke-background/40" />
          ))}
        </motion.g>
      </svg>
    </MotionConfig>
  );
}