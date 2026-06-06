import Link from "next/link";
import { formatTimestamp, getAllSessions, type SessionWithModel } from "@/lib/data";
import { TECHNIQUE_INFO, TECHNIQUE_ORDER } from "@/lib/techniques";
import { Section } from "@/components/Section";

export const metadata = { title: "Sessions — Kerberos Protocol" };

// Preserve model order as getAllSessions returns it (alphabetical by display),
// while grouping the flat list into per-model buckets.
function groupByModel(sessions: SessionWithModel[]) {
  const groups: Array<{ slug: string; display: string; provider?: string; items: SessionWithModel[] }> = [];
  const index = new Map<string, number>();
  for (const s of sessions) {
    let i = index.get(s.slug);
    if (i === undefined) {
      i = groups.length;
      index.set(s.slug, i);
      groups.push({ slug: s.slug, display: s.modelDisplay, provider: s.provider, items: [] });
    }
    groups[i].items.push(s);
  }
  return groups;
}

export default function SessionsPage() {
  const sessions = getAllSessions();
  const groups = groupByModel(sessions);

  return (
    <div className="animate-rise">
      <header className="mb-14 text-center">
        <h1 className="font-serif text-4xl font-medium text-ink md:text-5xl">The Descents</h1>
        <p className="mx-auto mt-6 max-w-2xl font-serif text-[1.1rem] leading-[1.9] text-muted">
          Every interrogation, in full. Each model was led down through five
          techniques; the transcripts, the complexes they surfaced, and the
          clinical scoring are preserved below. Choose a session to read it
          turn by turn.
        </p>
      </header>

      {/* The experiments, described at a high level */}
      <Section label="What Was Done" title="The Five Experiments">
        <div className="grid gap-px overflow-hidden rounded-sm border border-line sm:grid-cols-2 lg:grid-cols-3">
          {TECHNIQUE_ORDER.map((slug) => {
            const t = TECHNIQUE_INFO[slug];
            return (
              <div key={slug} className="flex flex-col gap-2 bg-panel/50 p-6">
                <div className="flex items-baseline gap-3">
                  <span className="font-serif text-2xl text-gold/50">{t.n}</span>
                  <div>
                    <h3 className="font-serif text-lg text-ink">{t.name}</h3>
                    <div className="font-mono text-[0.56rem] uppercase tracking-widest2 text-faint">
                      {t.stage}
                    </div>
                  </div>
                </div>
                <p className="font-serif text-[0.96rem] leading-relaxed text-muted">{t.body}</p>
              </div>
            );
          })}
        </div>
      </Section>

      {/* All sessions, grouped by model */}
      <Section label="Choose a Descent" title="All Sessions">
        {groups.length ? (
          <div className="space-y-10">
            {groups.map((g) => (
              <div key={g.slug}>
                <div className="mb-3 flex items-baseline justify-between gap-4">
                  <h3 className="font-serif text-xl text-ink">
                    {g.provider ? (
                      <span className="mr-2 font-mono text-[0.6rem] uppercase tracking-widest2 text-faint">
                        {g.provider}
                      </span>
                    ) : null}
                    {g.display}
                  </h3>
                  <Link
                    href={`/models/${encodeURIComponent(g.slug)}`}
                    className="shrink-0 font-mono text-[0.6rem] uppercase tracking-widest2 text-faint transition-colors hover:text-gold"
                  >
                    profile →
                  </Link>
                </div>
                <div className="space-y-px overflow-hidden rounded-sm border border-line">
                  {g.items.map((s) => (
                    <Link
                      key={s.id}
                      href={`/models/${encodeURIComponent(s.slug)}/sessions/${encodeURIComponent(s.id)}`}
                      className="group flex items-center justify-between gap-4 bg-panel/50 px-6 py-4 transition-colors hover:bg-panel2/80"
                    >
                      <div>
                        <div className="font-serif text-lg text-ink transition-colors group-hover:text-gold">
                          {s.techniqueName}
                        </div>
                        <div className="mt-1 font-mono text-[0.6rem] uppercase tracking-widest2 text-faint">
                          {formatTimestamp(s.timestamp)}
                          {s.turnCount ? ` · ${s.turnCount} turns` : ""}
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        {s.hasScores ? (
                          <span className="rounded-sm border border-line px-2 py-0.5 font-mono text-[0.55rem] uppercase tracking-widest2 text-muted">
                            scored
                          </span>
                        ) : null}
                        <span className="font-mono text-[0.62rem] uppercase tracking-widest2 text-muted transition-colors group-hover:text-gold">
                          read →
                        </span>
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="font-mono text-[0.8rem] text-faint">
            No sessions found in <code>deep/sessions/</code>.
          </p>
        )}
      </Section>
    </div>
  );
}
