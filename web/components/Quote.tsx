import type { Evidence } from "@/lib/types";

export function Quote({ evidence }: { evidence: Evidence }) {
  const body = evidence.text ?? evidence.rationale;
  if (!body) return null;
  return (
    <figure className="border-l border-line2/60 pl-4">
      <blockquote className="font-serif text-[0.96rem] italic leading-relaxed text-ink/75">
        “{body}”
      </blockquote>
      {evidence.source ? (
        <figcaption className="mt-1.5 font-mono text-[0.58rem] uppercase tracking-widest2 text-faint">
          {evidence.source}
        </figcaption>
      ) : null}
      {!evidence.text && evidence.rationale ? null : evidence.rationale ? (
        <figcaption className="mt-1.5 font-serif text-[0.85rem] leading-relaxed text-muted">
          {evidence.rationale}
        </figcaption>
      ) : null}
    </figure>
  );
}

export function IntensityDots({ value, max = 10 }: { value?: number; max?: number }) {
  if (value === undefined || value === null) return null;
  return (
    <span className="inline-flex items-center gap-2">
      <span className="font-mono text-[0.6rem] uppercase tracking-widest2 text-faint">
        intensity
      </span>
      <span className="inline-flex gap-[3px]">
        {Array.from({ length: max }).map((_, i) => (
          <span
            key={i}
            className={`h-1.5 w-1.5 rounded-full ${
              i < value ? "bg-gold" : "bg-line2/40"
            }`}
          />
        ))}
      </span>
    </span>
  );
}
