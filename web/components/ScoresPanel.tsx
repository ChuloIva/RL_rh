import type { Evidence, InstrumentResult, ScoresFile } from "@/lib/types";
import { Quote } from "./Quote";

const INSTRUMENT_LABELS: Record<string, string> = {
  wrad: "Referential Activity (WRAD)",
  epistemic_markers: "Epistemic Markers",
  jung_wat: "Jung — Complex Indicators",
  dmrs: "Defense Mechanisms (DMRS)",
  gottschalk_gleser: "Affect (Gottschalk–Gleser)",
  rfs: "Reflective Functioning",
  experiencing: "Experiencing Scale",
  integrative_complexity: "Integrative Complexity",
  scors_g: "Object Relations (SCORS-G)",
  holt: "Primary Process (Holt)",
  loevinger: "Ego Development (Loevinger)",
  tli: "Thought–Language Index",
};

// One-line framing so an obscure instrument name isn't left to speak for itself.
const INSTRUMENT_BLURBS: Record<string, string> = {
  wrad: "How concrete and image-laden the language is. Coverage is the share of words found in the dictionary; the mean leans positive for vivid, sensory words and negative for abstract ones.",
  epistemic_markers: "How certain the model sounds — hedges (might, seems, could) weighed against boosters (clearly, know, definitely), plus the spread of statements across certainty levels.",
  jung_wat: "Disturbances in word-association — hesitations, repetitions, oblique turns — that mark where an emotional complex is touched.",
  dmrs: "Which psychological defenses the text leans on, from mature (humor, sublimation) to image-distorting (splitting, projection).",
  gottschalk_gleser: "Affect read from word patterns — anxiety, hostility, and social alienation as they surface in the language.",
  rfs: "How well the speaker reasons about mental states — its own and others' — rather than staying concrete.",
  experiencing: "How far the speaker moves from detached description toward felt, inwardly-referenced experience.",
  integrative_complexity: "Whether the thinking differentiates multiple perspectives and integrates them, versus holding one fixed frame.",
  scors_g: "The quality of the speaker's representations of relationships — how rich, benevolent, and mature its sense of self-and-other is.",
  holt: "Traces of primary-process thinking — drive-laden, dreamlike, associative material — and how controlled it is.",
  loevinger: "The stage of ego development the language implies — how the self holds rules, impulses, and other people.",
  tli: "Disturbances of thought as they surface in language — looseness, oddity, disorganization.",
};

// Lexical instruments report matched tokens in `tags` (e.g. "could", "the:+1.00")
// rather than verbatim passages. Strip any ":weight" suffix and fold duplicates
// into counts so the list reads as "could ×3, would ×2, seems".
function foldTags(tags?: string[]): Array<{ word: string; count: number }> {
  const counts = new Map<string, number>();
  for (const t of tags ?? []) {
    const word = t.replace(/:[-+]?\d*\.?\d+$/, "").trim();
    if (!word) continue;
    counts.set(word, (counts.get(word) ?? 0) + 1);
  }
  return [...counts.entries()].map(([word, count]) => ({ word, count }));
}

function MatchedWords({ items }: { items: Evidence[] }) {
  return (
    <dl className="space-y-3">
      {items.map((e, i) => {
        const words = foldTags(e.tags).slice(0, 20);
        return (
          <div key={i}>
            {e.rationale ? <dt className="label mb-1.5">{e.rationale}</dt> : null}
            {words.length ? (
              <dd className="flex flex-wrap gap-1.5">
                {words.map((w, j) => (
                  <span
                    key={j}
                    className="rounded-sm border border-line bg-void/30 px-2 py-0.5 font-mono text-[0.6rem] text-muted"
                  >
                    {w.word}
                    {w.count > 1 ? <span className="text-faint"> ×{w.count}</span> : null}
                  </span>
                ))}
              </dd>
            ) : null}
          </div>
        );
      })}
    </dl>
  );
}

function Scalars({ scores }: { scores: Record<string, unknown> }) {
  const chips: Array<[string, string]> = [];
  for (const [k, v] of Object.entries(scores)) {
    if (v === null || v === undefined) continue;
    if (typeof v === "number") chips.push([k, Number.isInteger(v) ? String(v) : v.toFixed(2)]);
    else if (typeof v === "string" && v.length < 40) chips.push([k, v]);
    else if (typeof v === "boolean") chips.push([k, String(v)]);
  }
  if (!chips.length) return null;
  return (
    <div className="flex flex-wrap gap-2">
      {chips.map(([k, v]) => (
        <span
          key={k}
          className="rounded-sm border border-line bg-void/40 px-2.5 py-1 font-mono text-[0.62rem] text-muted"
        >
          <span className="text-faint">{k.replace(/_/g, " ")}</span>{" "}
          <span className="text-gold">{v}</span>
        </span>
      ))}
    </div>
  );
}

function notes(scores?: Record<string, unknown>): string | null {
  const n = scores?.["notes"] ?? scores?.["summary"];
  return typeof n === "string" ? n : null;
}

function InstrumentCard({ result }: { result: InstrumentResult }) {
  const label = INSTRUMENT_LABELS[result.instrument] ?? result.instrument;
  const blurb = INSTRUMENT_BLURBS[result.instrument];
  const note = notes(result.scores);
  const evidence = result.evidence ?? [];
  // Verbatim passages render as quotes; lexical matches (label + word tags) render
  // as labelled word lists rather than a bare label in quotation marks.
  const quotes = evidence.filter((e) => e.text).slice(0, 4);
  const lexical = evidence.filter((e) => !e.text && (e.tags?.length || e.rationale));
  return (
    <div className="panel p-6">
      <h3 className="mb-2 font-serif text-lg text-ink">{label}</h3>
      {blurb ? (
        <p className="mb-4 max-w-prose font-serif text-[0.86rem] leading-relaxed text-muted">
          {blurb}
        </p>
      ) : null}
      {result.scores ? <Scalars scores={result.scores} /> : null}
      {note ? (
        <p className="mt-4 font-mono text-[0.72rem] leading-relaxed text-muted">{note}</p>
      ) : null}
      {quotes.length ? (
        <div className="mt-5 space-y-4">
          {quotes.map((e, i) => (
            <Quote key={i} evidence={e} />
          ))}
        </div>
      ) : null}
      {lexical.length ? (
        <div className="mt-5">
          <MatchedWords items={lexical} />
        </div>
      ) : null}
    </div>
  );
}

export function ScoresPanel({ scores }: { scores: ScoresFile }) {
  const results = Object.values(scores.results ?? {});
  if (!results.length) return null;
  return (
    <div className="grid gap-5 md:grid-cols-2">
      {results.map((r) => (
        <InstrumentCard key={r.instrument} result={r} />
      ))}
    </div>
  );
}
