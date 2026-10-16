import { getScoreColorClass } from "../../lib/resume-insights";

interface ScoreRingProps {
  score: number;
  label: string;
  size?: "md" | "lg";
}

export default function ScoreRing({
  score,
  label,
  size = "md",
}: ScoreRingProps) {
  const scoreColor = getScoreColorClass(score);
  const px = size === "lg" ? 112 : 80;
  const text = size === "lg" ? "text-3xl" : "text-lg";
  const caption = size === "lg" ? "text-[10px]" : "text-[9px]";
  const strokeWidth = size === "lg" ? 7 : 8;

  return (
    <div className="relative shrink-0" style={{ width: px, height: px }}>
      <svg width={px} height={px} viewBox="0 0 100 100">
        <circle
          cx="50"
          cy="50"
          r="42"
          fill="none"
          stroke="hsl(var(--muted))"
          strokeWidth={strokeWidth}
        />
        <circle
          cx="50"
          cy="50"
          r="42"
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          strokeDasharray="264"
          strokeDashoffset={264 * (1 - score / 100)}
          strokeLinecap="round"
          className={scoreColor.text}
          style={{
            transform: "rotate(-90deg)",
            transformOrigin: "50% 50%",
            transition: "stroke-dashoffset 1s ease",
          }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`${text} font-bold tabular-nums ${scoreColor.text}`}>
          {score}
        </span>
        <span className={`${caption} text-muted-foreground`}>{label}</span>
      </div>
    </div>
  );
}
