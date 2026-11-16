import { cn } from "@/lib/utils";

const LETTERS = [["E", 65], ["X", 91], ["O", 117]];

// Still version of the loading animation's final frame: the bottle is the straight line of the "R".
export default function BottleLogo({ className, plain }) {
  return (
    <svg viewBox="12 18 96 114" className={cn("h-11 w-auto", className)} aria-hidden="true">
      <rect x="20" y="40" width="40" height="86" rx="6" className="fill-primary" />
      <rect x="16" y="22" width="48" height="16" rx="4" className="fill-foreground" />
      {[28, 36, 44, 52].map((x) => (
        <line key={x} x1={x} x2={x} y1="26" y2="34" strokeWidth="2" strokeLinecap="round" className="stroke-background/40" />
      ))}
      {!plain && LETTERS.map(([char, y]) => (
        <text key={char} x="40" y={y} textAnchor="middle" fontSize="22" className="fill-primary-foreground font-display font-semibold">{char}</text>
      ))}
      <path d="M60 46 H76 a20 20 0 0 1 0 40 H60" strokeWidth="11" className="fill-none stroke-primary" />
      <path d="M72 88 L98 124" strokeWidth="11" strokeLinecap="round" className="fill-none stroke-primary" />
    </svg>
  );
}