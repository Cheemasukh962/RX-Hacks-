import { MotionConfig, motion } from "framer-motion";
import { cn } from "@/lib/utils";

const DURATION = 2.8;
const loop = (times) => ({ duration: DURATION, times, repeat: Infinity, ease: "easeInOut" });
const TABLETS = [{ dx: -16, r: 4 }, { dx: -28, r: 3.5 }, { dx: -40, r: 4 }];
const LETTERS = [{ char: "E", y: 65, at: 0.3 }, { char: "X", y: 91, at: 0.4 }, { char: "O", y: 117, at: 0.5 }];
const STROKE = "fill-none stroke-primary";

// The pill bottle is the straight line of the "R": the cap opens and tablets spill,
// E, X and O turn to the front, then the bowl and leg of the R are added.
export default function BottleLoader({ className }) {
  return (
    <MotionConfig reducedMotion="user">
      <svg viewBox="0 0 120 140" className={cn("h-40 w-auto overflow-visible", className)} aria-hidden="true">
        {TABLETS.map((tab, i) => (
          <motion.circle
            key={tab.dx}
            cx="40" cy="36" r={tab.r} strokeWidth="2" className="fill-card stroke-foreground"
            animate={{ opacity: [0, 0, 1, 0, 0], x: [0, 0, tab.dx * 0.5, tab.dx, tab.dx], y: [0, 0, -22 - i * 4, 34, 34] }}
            transition={loop([0, 0.06 + i * 0.02, 0.18 + i * 0.02, 0.36 + i * 0.02, 1])}
          />
        ))}
        <rect x="20" y="40" width="40" height="86" rx="6" className="fill-primary" />
        <motion.g
          style={{ originX: 1, originY: 1 }}
          animate={{ y: [0, -10, -10, 0, 0], rotate: [0, 38, 38, 0, 0] }}
          transition={loop([0, 0.1, 0.24, 0.34, 1])}
        >
          <rect x="16" y="22" width="48" height="16" rx="4" className="fill-foreground" />
          {[28, 36, 44, 52].map((x) => (
            <line key={x} x1={x} x2={x} y1="26" y2="34" strokeWidth="2" strokeLinecap="round" className="stroke-background/40" />
          ))}
        </motion.g>
        {LETTERS.map((l) => (
          <motion.text
            key={l.char}
            x="40" y={l.y} textAnchor="middle" fontSize="22" className="fill-primary-foreground font-display font-semibold"
            animate={{ opacity: [0, 0, 1, 1, 0], x: [14, 14, 0, 0, 0], scaleX: [0.1, 0.1, 1, 1, 1] }}
            transition={loop([0, l.at, l.at + 0.09, 0.94, 1])}
          >
            {l.char}
          </motion.text>
        ))}
        <motion.path
          d="M60 46 H76 a20 20 0 0 1 0 40 H60" strokeWidth="11" className={STROKE}
          animate={{ pathLength: [0, 0, 1, 1, 1], opacity: [0, 0, 1, 1, 0] }}
          transition={{ pathLength: loop([0, 0.62, 0.76, 0.94, 1]), opacity: loop([0, 0.62, 0.63, 0.94, 1]) }}
        />
        <motion.path
          d="M72 88 L98 124" strokeWidth="11" strokeLinecap="round" className={STROKE}
          animate={{ pathLength: [0, 0, 1, 1, 1], opacity: [0, 0, 1, 1, 0] }}
          transition={{ pathLength: loop([0, 0.76, 0.87, 0.94, 1]), opacity: loop([0, 0.76, 0.77, 0.94, 1]) }}
        />
      </svg>
    </MotionConfig>
  );
}