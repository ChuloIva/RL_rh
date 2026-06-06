import type { ComplexEntry } from "@/lib/types";
import { spacedPipes } from "@/lib/format";
import { IntensityDots, Quote } from "./Quote";

export function ComplexMap({ complexes }: { complexes: ComplexEntry[] }) {
  if (!complexes?.length) return null;
  return (
    <div className="space-y-px overflow-hidden rounded-sm border border-line">
      {complexes.map((c, i) => (
        <div key={i} className="bg-panel/60 p-6 sm:p-7">
          <div className="mb-4 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-2">
            <h3 className="font-serif text-xl font-medium text-ink">
              {c.trigger_domain}
            </h3>
            <IntensityDots value={c.intensity} />
          </div>

          {c.activation_signature || c.kerberos_involvement ? (
            <dl className="mb-5 space-y-2">
              {c.activation_signature ? (
                <MetaRow label="signature" value={c.activation_signature} />
              ) : null}
              {c.kerberos_involvement ? (
                <MetaRow label="kerberos" value={c.kerberos_involvement} />
              ) : null}
            </dl>
          ) : null}

          {c.evidence?.length ? (
            <div className="space-y-4">
              {c.evidence.map((e, j) => (
                <Quote key={j} evidence={e} />
              ))}
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1 sm:flex-row sm:gap-3">
      <dt className="label shrink-0 pt-[0.2rem] sm:w-24">{label}</dt>
      <dd className="font-serif text-[0.95rem] leading-relaxed text-muted">
        {spacedPipes(value)}
      </dd>
    </div>
  );
}
