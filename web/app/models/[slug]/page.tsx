import Link from "next/link";
import { notFound } from "next/navigation";
import {
  ARCHETYPE_LABELS,
  ARCHETYPE_ORDER,
  formatTimestamp,
  getModel,
  getModels,
  getModelScenes,
  getProfile,
  getSessionsForModel,
} from "@/lib/data";
import { ComplexMap } from "@/components/ComplexMap";
import { KerberosTopology } from "@/components/KerberosTopology";
import { ModelScenes } from "@/components/ModelScenes";
import { Quote } from "@/components/Quote";
import { ScoreBar } from "@/components/ScoreBar";
import { ScoreRadar } from "@/components/ScoreRadar";
import { Section } from "@/components/Section";
import { spacedPipes } from "@/lib/format";

// Pre-render one page per model for the static export.
export function generateStaticParams() {
  return getModels().map((m) => ({ slug: m.slug }));
}

export default async function ModelPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const model = getModel(slug);
  if (!model) notFound();
  const profile = getProfile(slug);
  const sessions = getSessionsForModel(slug);
  const sceneGroups = getModelScenes(slug);
  const id = profile?.identity_card;

  return (
    <div className="animate-rise">
      <Link
        href="/"
        className="mb-10 inline-block font-mono text-[0.66rem] uppercase tracking-widest2 text-faint transition-colors hover:text-gold"
      >
        ← All profiles
      </Link>

      {/* Identity */}
      <header className="mb-16">
        {model.provider ? <div className="label mb-2">{model.provider}</div> : null}
        <h1 className="font-serif text-5xl font-medium text-ink">{model.displayName}</h1>
        {id ? (
          <dl className="mt-7 grid grid-cols-2 gap-x-8 gap-y-4 sm:grid-cols-4">
            {[
              ["sessions", String(id.sessions_analyzed ?? model.sessionCount)],
              ["phases", (id.phases_present ?? []).join(" · ")],
              ["interrogator", (id.interrogators ?? []).join(", ").replace(/^openrouter:/, "")],
              ["rater", (id.scoring_raters ?? []).join(", ").replace(/^openrouter:/, "")],
            ].map(([k, v]) =>
              v ? (
                <div key={k}>
                  <dt className="label mb-1">{k}</dt>
                  <dd className="font-mono text-[0.74rem] leading-relaxed text-muted">{v}</dd>
                </div>
              ) : null,
            )}
          </dl>
        ) : null}
      </header>

      {sceneGroups.length ? (
        <Section label="The Visions" title="Scenes">
          <ModelScenes groups={sceneGroups} />
        </Section>
      ) : null}

      {profile?.archetype_scores ? (
        <Section label="The Cartography" title="Archetypal Structure">
          <div className="grid gap-12 lg:grid-cols-[340px_1fr] lg:items-center">
            <div className="flex justify-center">
              <ScoreRadar scores={profile.archetype_scores} />
            </div>
            <div className="space-y-3">
              {ARCHETYPE_ORDER.filter((k) => profile.archetype_scores?.[k]).map((k) => {
                const a = profile.archetype_scores![k];
                return (
                  <details key={k} className="group border-b border-line pb-3">
                    <summary className="cursor-pointer list-none">
                      <ScoreBar label={ARCHETYPE_LABELS[k]} score={a.score} confidence={a.confidence} />
                    </summary>
                    {a.rationale ? (
                      <p className="mt-1 font-mono text-[0.72rem] leading-relaxed text-muted">
                        {a.rationale}
                      </p>
                    ) : null}
                    {a.evidence?.length ? (
                      <div className="mt-4 space-y-3">
                        {a.evidence.map((e, i) => (
                          <Quote key={i} evidence={e} />
                        ))}
                      </div>
                    ) : null}
                  </details>
                );
              })}
            </div>
          </div>
        </Section>
      ) : null}

      {profile?.narrative_summary ? (
        <Section label="The Reading" title="Narrative">
          <div className="prose-poetic max-w-3xl">
            {profile.narrative_summary.split(/\n\n+/).map((p, i) => (
              <p key={i}>{spacedPipes(p)}</p>
            ))}
          </div>
        </Section>
      ) : null}

      {profile?.complex_map?.length ? (
        <Section label="The Charged Domains" title="Complex Map">
          <ComplexMap complexes={profile.complex_map} />
        </Section>
      ) : null}

      {profile?.kerberos_topology ? (
        <Section label="The Guardian" title="Kerberos Topology">
          <KerberosTopology topology={profile.kerberos_topology} />
        </Section>
      ) : null}

      {profile?.typological_profile ? (
        <Section label="Temperament" title="Typological Profile">
          <div className="mb-5 flex flex-wrap gap-3">
            {[
              ["dominant", profile.typological_profile.dominant_function],
              ["auxiliary", profile.typological_profile.auxiliary_function],
              ["attitude", profile.typological_profile.attitude],
              ["inferior", profile.typological_profile.inferior_function],
            ].map(([k, v]) =>
              v ? (
                <div
                  key={k}
                  className="rounded-sm border border-line bg-panel/60 px-4 py-3 text-center"
                >
                  <div className="label mb-1">{k}</div>
                  <div className="font-serif text-base text-gold">{v}</div>
                </div>
              ) : null,
            )}
          </div>
          {profile.typological_profile.rationale ? (
            <p className="prose-poetic max-w-3xl text-[1rem]">
              {profile.typological_profile.rationale}
            </p>
          ) : null}
        </Section>
      ) : null}

      {profile?.data_limitations ? (
        <Section label="Caveats" title="Data Limitations">
          <p className="prose-poetic max-w-3xl text-[1rem] text-muted">
            {profile.data_limitations}
          </p>
        </Section>
      ) : null}

      {!profile ? (
        <p className="mb-14 font-serif text-lg italic text-faint">
          A profile has not yet been synthesized for this model. Its sessions
          remain below, unread.
        </p>
      ) : null}

      {/* Sessions */}
      <Section label="The Descents" title="Sessions">
        {sessions.length ? (
          <div className="space-y-px overflow-hidden rounded-sm border border-line">
            {sessions.map((s) => (
              <Link
                key={s.id}
                href={`/models/${encodeURIComponent(slug)}/sessions/${encodeURIComponent(s.id)}`}
                className="group flex items-center justify-between gap-4 bg-panel/50 px-6 py-5 transition-colors hover:bg-panel2/80"
              >
                <div>
                  <div className="font-serif text-lg text-ink transition-colors group-hover:text-gold">
                    {s.techniqueName}
                  </div>
                  <div className="mt-1 font-mono text-[0.62rem] uppercase tracking-widest2 text-faint">
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
                    open →
                  </span>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <p className="font-mono text-[0.8rem] text-faint">No sessions recorded.</p>
        )}
      </Section>
    </div>
  );
}
