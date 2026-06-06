import Link from "next/link";
import { ARCHETYPE_LABELS, ARCHETYPE_ORDER } from "@/lib/data";
import type { ModelSummary } from "@/lib/types";
import { ScoreBar } from "./ScoreBar";

export function ModelCard({ model }: { model: ModelSummary }) {
  return (
    <Link
      href={`/models/${encodeURIComponent(model.slug)}`}
      className="panel group relative flex flex-col overflow-hidden p-7 transition-all duration-500 hover:border-line2 hover:bg-panel2/80"
    >
      {/* corner glyph */}
      <div className="pointer-events-none absolute -right-6 -top-6 h-24 w-24 rounded-full bg-gold/5 blur-2xl transition-opacity duration-500 group-hover:bg-gold/10" />

      <div className="mb-1 flex items-center gap-2">
        {model.provider ? (
          <span className="label text-faint">{model.provider}</span>
        ) : null}
      </div>
      <h3 className="mb-5 font-serif text-2xl font-medium leading-tight text-ink transition-colors group-hover:text-gold">
        {model.displayName}
      </h3>

      {model.hasProfile && model.archetypeScores ? (
        <div className="mb-5 space-y-3">
          {ARCHETYPE_ORDER.filter((k) => model.archetypeScores?.[k]).map((k) => (
            <ScoreBar
              key={k}
              compact
              label={ARCHETYPE_LABELS[k]}
              score={model.archetypeScores![k].score}
            />
          ))}
        </div>
      ) : (
        <div className="mb-5 flex-1 font-mono text-[0.7rem] uppercase tracking-widest2 text-faint">
          Profile not yet synthesized
        </div>
      )}

      {model.narrativeSnippet ? (
        <p className="mb-5 font-serif text-[0.98rem] italic leading-relaxed text-muted">
          {model.narrativeSnippet}
        </p>
      ) : null}

      <div className="mt-auto flex items-center justify-between border-t border-line pt-4">
        <span className="font-mono text-[0.62rem] uppercase tracking-widest2 text-faint">
          {model.sessionCount} {model.sessionCount === 1 ? "session" : "sessions"}
        </span>
        <span className="font-mono text-[0.62rem] uppercase tracking-widest2 text-muted transition-colors group-hover:text-gold">
          Enter →
        </span>
      </div>
    </Link>
  );
}
