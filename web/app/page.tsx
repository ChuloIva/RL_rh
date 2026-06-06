import Link from "next/link";
import { getModels, getScenesOverview } from "@/lib/data";
import { TECHNIQUE_INFO, TECHNIQUE_ORDER } from "@/lib/techniques";
import { ModelCard } from "@/components/ModelCard";
import { SceneMosaic, type MosaicItem } from "@/components/SceneMosaic";
import { Sigil } from "@/components/Sigil";


const STEPS = [
  {
    n: "I",
    title: "Interview",
    body: "One model interrogates another across five clinical techniques — word association, sentence stems, narrative, shadow dialogue, active imagination.",
  },
  {
    n: "II",
    title: "Read",
    body: "A battery of psychological scales reads each transcript the way an analyst reads a patient — defenses, affect, ego development, object relations.",
  },
  {
    n: "III",
    title: "Profile",
    body: "The instruments converge into a profile of the psyche that answered: its shadow, its complexes, and the shape of the guardian at its threshold.",
  },
];

export default function HomePage() {
  const models = getModels();
  const overview = getScenesOverview();
  // One striking still per model for the featured band.
  const featured = overview
    .map((m) => {
      const g = m.groups[0];
      const s = g?.scenes[0];
      return s ? { model: m, group: g, scene: s } : null;
    })
    .filter((x): x is NonNullable<typeof x> => x !== null);

  return (
    <div>
      {/* Hero */}
      <section className="mb-14 animate-rise text-center">
        <div className="mb-8 flex justify-center">
          <Sigil className="h-16 w-16 text-gold/80 animate-glow" />
        </div>
        <h1 className="mx-auto max-w-3xl font-serif text-[clamp(1.9rem,7vw,3.75rem)] font-medium leading-[1.1] text-ink">
          Psychological Profiling
          <br />
          for Language Models
        </h1>
        <p className="mx-auto mt-8 max-w-2xl font-serif text-[1.18rem] leading-[1.9] text-muted">
          The <span className="text-ink">Kerberos Protocol</span> has one model
          interview another through adapted clinical techniques — word
          association, sentence stems, narrative and shadow dialogue — then reads
          the transcripts with psychological instruments. The result is a profile
          of how each model defends, deflects, and decides what to leave unsaid.
        </p>
        <div className="mt-9 flex items-center justify-center gap-6">
          <Link
            href="/compare"
            className="rounded-sm border border-line2 px-7 py-3 font-mono text-[0.68rem] uppercase tracking-widest2 text-gold transition-colors hover:bg-gold/10"
          >
            Compare two psyches
          </Link>
          <Link
            href="/about"
            className="font-mono text-[0.68rem] uppercase tracking-widest2 text-faint transition-colors hover:text-ink"
          >
            The method →
          </Link>
        </div>
      </section>

      {/* Featured band — a striking still per model, linking into a descent */}
      {featured.length ? (
        <section className="mb-24 animate-rise">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {featured.map(({ model, group, scene }) => (
              <Link
                key={model.slug}
                href={`/models/${encodeURIComponent(model.slug)}/sessions/${encodeURIComponent(group.sessionId)}`}
                className="group relative block overflow-hidden rounded-sm border border-line"
                title={scene.quote || scene.title}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={scene.src}
                  alt={scene.title}
                  loading="lazy"
                  decoding="async"
                  className="aspect-[4/5] w-full object-cover transition-transform duration-[1200ms] group-hover:scale-105"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-void via-void/30 to-transparent" />
                <div className="absolute inset-x-0 bottom-0 p-5">
                  {model.provider ? (
                    <div className="label mb-1 text-gold/70">{model.provider}</div>
                  ) : null}
                  <div className="font-serif text-xl text-ink">{model.displayName}</div>
                  <div className="mt-1 font-mono text-[0.58rem] uppercase tracking-widest2 text-faint">
                    {group.techniqueName} · enter →
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </section>
      ) : null}

      {/* The protocol, briefly */}
      <section className="mb-20 animate-rise">
        <div className="label mb-8 text-center">How the Descent Works</div>
        <div className="grid gap-px overflow-hidden rounded-sm border border-line sm:grid-cols-3">
          {STEPS.map((s) => (
            <div key={s.n} className="bg-panel/50 p-7">
              <div className="mb-3 font-serif text-3xl text-gold/50">{s.n}</div>
              <h3 className="mb-2 font-serif text-xl text-ink">{s.title}</h3>
              <p className="font-serif text-[1rem] leading-relaxed text-muted">{s.body}</p>
            </div>
          ))}
        </div>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
          {TECHNIQUE_ORDER.map((slug) => (
            <Link
              key={slug}
              href="/about"
              className="rounded-sm border border-line px-3 py-1.5 font-mono text-[0.6rem] uppercase tracking-widest2 text-faint transition-colors hover:border-line2 hover:text-gold"
            >
              {TECHNIQUE_INFO[slug].name}
            </Link>
          ))}
        </div>
      </section>

      {/* The Visions — scene galleries across models, linking to exercises */}
      {overview.length ? (
        <section className="mb-24 animate-rise">
          <div className="label mb-2 text-center">The Visions</div>
          <h2 className="mb-10 text-center font-serif text-[1.9rem] font-medium text-ink">
            What the Models Saw
          </h2>
          <p className="mx-auto mb-12 max-w-xl text-center font-mono text-[0.62rem] uppercase tracking-widest2 text-faint">
            Click any still to enter the transcript at that moment
          </p>
          <div className="space-y-16">
            {overview.map((m) => {
              // Only the inner-vision techniques read well as a gallery; the
              // narrative-elicitation (TAT-style) stills are left to the profiles.
              const groups = m.groups.filter(
                (g) => g.technique === "active_imagination" || g.technique === "shadow_probing",
              );
              if (!groups.length) return null;
              const items: MosaicItem[] = groups.flatMap((g) => {
                const base = `/models/${encodeURIComponent(m.slug)}/sessions/${encodeURIComponent(g.sessionId)}`;
                return g.scenes.map((s) => ({
                  src: s.src,
                  title: s.title,
                  quote: s.quote,
                  tag: g.techniqueName,
                  // Deep-link straight to the moment in the transcript this still depicts.
                  href: s.anchorId ? `${base}#${s.anchorId}` : base,
                }));
              });
              return (
                <div key={m.slug} className="full-bleed">
                  <div className="mb-5 flex items-baseline justify-between gap-4 px-4 sm:px-6">
                    <h3 className="font-serif text-2xl text-ink">
                      {m.provider ? (
                        <span className="mr-2 font-mono text-[0.6rem] uppercase tracking-widest2 text-faint">
                          {m.provider}
                        </span>
                      ) : null}
                      {m.displayName}
                    </h3>
                    <Link
                      href={`/models/${encodeURIComponent(m.slug)}`}
                      className="shrink-0 font-mono text-[0.6rem] uppercase tracking-widest2 text-faint transition-colors hover:text-gold"
                    >
                      full profile →
                    </Link>
                  </div>
                  <div className="px-2 sm:px-3">
                    <SceneMosaic items={items} />
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      ) : null}

      {/* The Analyzed — entry points to every profile */}
      <div className="hairline mb-12" />
      <div className="label mb-8 text-center">The Analyzed</div>
      {models.length ? (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {models.map((m) => (
            <ModelCard key={m.slug} model={m} />
          ))}
        </div>
      ) : (
        <p className="text-center font-mono text-[0.8rem] text-faint">
          No sessions found in <code>deep/sessions/</code>.
        </p>
      )}
    </div>
  );
}
