export function ScoreBar({
  label,
  score,
  max = 10,
  confidence,
  compact = false,
}: {
  label: string;
  score: number;
  max?: number;
  confidence?: string;
  compact?: boolean;
}) {
  const pct = Math.max(0, Math.min(1, score / max)) * 100;
  return (
    <div className={compact ? "" : "mb-4"}>
      <div className="mb-1.5 flex items-baseline justify-between gap-3">
        <span
          className={
            compact
              ? "font-mono text-[0.6rem] uppercase tracking-widest2 text-muted"
              : "font-mono text-[0.66rem] uppercase tracking-widest2 text-muted"
          }
        >
          {label}
        </span>
        <span className="font-mono text-[0.7rem] text-gold">
          {score}
          <span className="text-faint">/{max}</span>
          {confidence ? (
            <span className="ml-2 text-faint">· {confidence}</span>
          ) : null}
        </span>
      </div>
      <div className="h-px w-full bg-line2/40">
        <div
          className="h-px bg-gradient-to-r from-ember/70 to-gold"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
