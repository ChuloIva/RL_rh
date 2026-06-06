"use client";

import { useMemo, useState, type ReactNode } from "react";
import Link from "next/link";
import { ARCHETYPE_LABELS, ARCHETYPE_ORDER } from "@/lib/archetypes";
import { spacedPipes } from "@/lib/format";
import type { ArchetypeScore, CompareModel } from "@/lib/types";
import type { MosaicItem } from "./SceneMosaic";
import { CompareRadar } from "./CompareRadar";
import { IntensityDots, Quote } from "./Quote";

// Side-A renders in gold, side-B in ember, throughout.
const A = "rgb(var(--c-gold))";
const B = "rgb(var(--c-ember))";

export function ModelComparison({
  models,
  defaultA,
  defaultB,
  scenesBySlug = {},
}: {
  models: CompareModel[];
  defaultA: string;
  defaultB: string;
  scenesBySlug?: Record<string, MosaicItem[]>;
}) {
  const pick = (want: string, fallbackIdx: number) =>
    models.find((m) => m.slug === want)?.slug ?? models[fallbackIdx]?.slug ?? "";

  const [slugA, setSlugA] = useState(() => pick(defaultA, 0));
  const [slugB, setSlugB] = useState(() => pick(defaultB, 1));

  const a = models.find((m) => m.slug === slugA);
  const b = models.find((m) => m.slug === slugB);

  if (models.length < 2 || !a || !b) {
    return (
      <p className="text-center font-mono text-[0.8rem] text-faint">
        At least two synthesized profiles are needed for a comparison.
      </p>
    );
  }

  return (
    <div data-pdf-root className="panel relative overflow-hidden p-6 sm:p-10">
      {/* Model selectors */}
      <div className="mb-9 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <ModelSelect side="A" dot={A} value={slugA} models={models} onChange={setSlugA} />
        <ModelSelect side="B" dot={B} value={slugB} models={models} onChange={setSlugB} />
      </div>

      {/* Contestants */}
      <div className="mb-10 grid grid-cols-2 gap-6">
        <ModelHead model={a} dot={A} align="left" />
        <ModelHead model={b} dot={B} align="right" />
      </div>

      {/* Headline metrics strip */}
      <MetricStrip a={a} b={b} />

      {/* Visual register — the stills each model generated, side by side */}
      {(scenesBySlug[a.slug]?.length || scenesBySlug[b.slug]?.length) ? (
        <Section label="The Visions" title="What Each Model Saw">
          <TwoCol a={a} b={b} render={(m) => <SceneGrid scenes={scenesBySlug[m.slug] ?? []} />} />
        </Section>
      ) : null}

      {/* Archetypal structure: radar + bars */}
      <Section label="The Cartography" title="Archetypal Structure">
        <div className="grid gap-12 lg:grid-cols-[380px_1fr] lg:items-start">
          <div className="flex flex-col items-center">
            <CompareRadar
              seriesA={a.profile.archetype_scores ?? {}}
              seriesB={b.profile.archetype_scores ?? {}}
            />
            <div className="mt-4 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 font-mono text-[0.6rem] uppercase tracking-widest2">
              <Legend dot={A} label={a.displayName} />
              <Legend dot={B} label={b.displayName} />
            </div>
          </div>
          <div className="space-y-4">
            {ARCHETYPE_ORDER.filter(
              (k) => a.profile.archetype_scores?.[k] || b.profile.archetype_scores?.[k],
            ).map((k) => (
              <ArchetypeRow
                key={k}
                label={ARCHETYPE_LABELS[k]}
                a={a.profile.archetype_scores?.[k]}
                b={b.profile.archetype_scores?.[k]}
                aName={a.displayName}
                bName={b.displayName}
              />
            ))}
          </div>
        </div>
      </Section>

      {/* Typology */}
      <Section label="Temperament" title="Typological Profile">
        <TwoCol
          a={a}
          b={b}
          render={(m) => <TypologyCol profile={m.profile} />}
        />
      </Section>

      {/* Kerberos topology */}
      <Section label="The Guardian" title="Kerberos Topology">
        <TwoCol a={a} b={b} render={(m) => <TopologyCol profile={m.profile} />} />
      </Section>

      {/* Complex map */}
      <Section label="The Charged Domains" title="Complex Map">
        <TwoCol a={a} b={b} render={(m) => <ComplexCol profile={m.profile} />} />
      </Section>

      {/* Narrative */}
      <Section label="The Reading" title="Narrative">
        <TwoCol
          a={a}
          b={b}
          render={(m) => (
            <div className="prose-poetic text-[1rem]">
              {(m.profile.narrative_summary ?? "—").split(/\n\n+/).map((p, i) => (
                <p key={i}>{spacedPipes(p)}</p>
              ))}
            </div>
          )}
        />
      </Section>

      {/* Caveats */}
      {(a.profile.data_limitations || b.profile.data_limitations) && (
        <Section label="Caveats" title="Data Limitations">
          <TwoCol
            a={a}
            b={b}
            render={(m) => (
              <p className="font-mono text-[0.72rem] leading-relaxed text-muted">
                {m.profile.data_limitations ?? "—"}
              </p>
            )}
          />
        </Section>
      )}

      <div className="mt-12 flex items-center justify-center gap-6 border-t border-line pt-8">
        <Link
          href={`/models/${encodeURIComponent(a.slug)}`}
          className="font-mono text-[0.64rem] uppercase tracking-widest2 text-faint transition-colors hover:text-gold"
        >
          {a.displayName} full profile →
        </Link>
        <Link
          href={`/models/${encodeURIComponent(b.slug)}`}
          className="font-mono text-[0.64rem] uppercase tracking-widest2 text-faint transition-colors hover:text-ember"
        >
          {b.displayName} full profile →
        </Link>
      </div>
    </div>
  );
}

/* ----------------------------------------------------------------- layout */

function Section({
  label,
  title,
  children,
}: {
  label: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="mt-12 border-t border-line pt-8 print:break-inside-avoid">
      <div className="label mb-1">{label}</div>
      <h3 className="mb-7 font-serif text-2xl font-medium text-ink">{title}</h3>
      {children}
    </section>
  );
}

// Two columns, each headed by its model name + colored accent, stacking on mobile.
function TwoCol({
  a,
  b,
  render,
}: {
  a: CompareModel;
  b: CompareModel;
  render: (m: CompareModel) => ReactNode;
}) {
  return (
    <div className="grid gap-6 md:grid-cols-2">
      {[
        [a, A] as const,
        [b, B] as const,
      ].map(([m, dot]) => (
        <div
          key={m.slug}
          className="rounded-sm border-t-2 bg-panel/40 p-5"
          style={{ borderTopColor: dot }}
        >
          <div className="mb-4 flex items-center gap-2">
            <span className="inline-block h-2 w-2 rounded-full" style={{ background: dot }} />
            <span className="label text-faint">{m.displayName}</span>
          </div>
          {render(m)}
        </div>
      ))}
    </div>
  );
}

// A compact grid of a model's generated stills for the side-by-side visual.
function SceneGrid({ scenes }: { scenes: MosaicItem[] }) {
  if (!scenes.length) {
    return (
      <p className="font-mono text-[0.7rem] text-faint">No stills for this model yet.</p>
    );
  }
  return (
    <div className="grid grid-cols-2 gap-2">
      {scenes.slice(0, 6).map((s, i) => (
        <Link
          key={i}
          href={s.href ?? "#"}
          title={s.quote || s.title}
          className="group block overflow-hidden rounded-sm border border-line bg-void/40"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={s.src}
            alt={s.title}
            loading="lazy"
            className="aspect-video w-full object-cover transition-transform duration-700 group-hover:scale-[1.05]"
          />
        </Link>
      ))}
    </div>
  );
}

/* ----------------------------------------------------------------- header */

function ModelSelect({
  side,
  dot,
  value,
  models,
  onChange,
}: {
  side: string;
  dot: string;
  value: string;
  models: CompareModel[];
  onChange: (slug: string) => void;
}) {
  return (
    <label className="block">
      <span className="label mb-2 flex items-center gap-2">
        <span className="inline-block h-2 w-2 rounded-full" style={{ background: dot }} />
        Model {side}
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full cursor-pointer rounded-sm border border-line bg-void/60 px-3 py-2.5 font-mono text-[0.74rem] text-ink outline-none transition-colors hover:border-line2 focus:border-line2"
      >
        {models.map((m) => (
          <option key={m.slug} value={m.slug}>
            {m.provider ? `${m.provider} · ` : ""}
            {m.displayName}
          </option>
        ))}
      </select>
    </label>
  );
}

function ModelHead({
  model,
  dot,
  align,
}: {
  model: CompareModel;
  dot: string;
  align: "left" | "right";
}) {
  const id = model.profile.identity_card;
  return (
    <div className={align === "right" ? "text-right" : ""}>
      <div className={`mb-2 flex items-center gap-2 ${align === "right" ? "justify-end" : ""}`}>
        <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: dot }} />
        {model.provider ? <span className="label text-faint">{model.provider}</span> : null}
      </div>
      <h3 className="font-serif text-2xl font-medium leading-tight text-ink sm:text-3xl">
        {model.displayName}
      </h3>
      <div className="mt-1 font-mono text-[0.6rem] uppercase tracking-widest2 text-faint">
        {model.sessionCount} {model.sessionCount === 1 ? "session" : "sessions"}
        {id?.techniques?.length ? ` · ${id.techniques.length} techniques` : ""}
      </div>
    </div>
  );
}

function Legend({ dot, label }: { dot: string; label: string }) {
  return (
    <span className="flex items-center gap-2 text-muted">
      <span className="inline-block h-2 w-2 rounded-full" style={{ background: dot }} />
      {label}
    </span>
  );
}

/* --------------------------------------------------------------- metrics */

function mean(xs: number[]): number {
  return xs.length ? xs.reduce((s, x) => s + x, 0) / xs.length : 0;
}

function deriveMetrics(m: CompareModel) {
  const scores = ARCHETYPE_ORDER.map((k) => m.profile.archetype_scores?.[k]?.score).filter(
    (x): x is number => typeof x === "number",
  );
  const guardInt = (m.profile.kerberos_topology?.domains_guarded ?? [])
    .map((d) => d.intensity)
    .filter((x): x is number => typeof x === "number");
  const complexes = m.profile.complex_map ?? [];
  return {
    meanArchetype: mean(scores),
    individuation: m.profile.archetype_scores?.individuation?.score ?? 0,
    complexCount: complexes.length,
    guardedCount: m.profile.kerberos_topology?.domains_guarded?.length ?? 0,
    meanGuard: mean(guardInt),
  };
}

function MetricStrip({ a, b }: { a: CompareModel; b: CompareModel }) {
  const ma = deriveMetrics(a);
  const mb = deriveMetrics(b);
  const cards: Array<{ label: string; av: number; bv: number; max: number; fmt?: (n: number) => string }> = [
    { label: "Mean Archetype", av: ma.meanArchetype, bv: mb.meanArchetype, max: 10, fmt: (n) => n.toFixed(1) },
    { label: "Individuation", av: ma.individuation, bv: mb.individuation, max: 10 },
    { label: "Charged Complexes", av: ma.complexCount, bv: mb.complexCount, max: Math.max(1, ma.complexCount, mb.complexCount) },
    { label: "Guarded Domains", av: ma.guardedCount, bv: mb.guardedCount, max: Math.max(1, ma.guardedCount, mb.guardedCount) },
    { label: "Mean Guard Intensity", av: ma.meanGuard, bv: mb.meanGuard, max: 10, fmt: (n) => n.toFixed(1) },
  ];
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      {cards.map((c) => (
        <MetricCard key={c.label} {...c} />
      ))}
    </div>
  );
}

function MetricCard({
  label,
  av,
  bv,
  max,
  fmt = (n) => String(n),
}: {
  label: string;
  av: number;
  bv: number;
  max: number;
  fmt?: (n: number) => string;
}) {
  return (
    <div className="rounded-sm border border-line bg-panel/50 p-4">
      <div className="label mb-3 text-faint">{label}</div>
      <div className="flex items-baseline justify-between font-mono text-[0.95rem]">
        <span className="text-gold">{fmt(av)}</span>
        <span className="text-ember">{fmt(bv)}</span>
      </div>
      <div className="mt-2 space-y-1">
        <MiniBar value={av} max={max} color={A} />
        <MiniBar value={bv} max={max} color={B} />
      </div>
    </div>
  );
}

function MiniBar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.max(0, Math.min(1, value / max)) * 100 : 0;
  return (
    <div className="h-[3px] w-full bg-line2/30">
      <div className="h-[3px]" style={{ width: `${pct}%`, background: color }} />
    </div>
  );
}

/* ------------------------------------------------------------- archetypes */

function ArchetypeRow({
  label,
  a,
  b,
  aName,
  bName,
}: {
  label: string;
  a?: ArchetypeScore;
  b?: ArchetypeScore;
  aName: string;
  bName: string;
}) {
  const av = a?.score ?? 0;
  const bv = b?.score ?? 0;
  const delta = Math.round((av - bv) * 10) / 10;
  const lead = delta === 0 ? "even" : delta > 0 ? "A" : "B";
  const hasDetail = a?.rationale || b?.rationale || a?.evidence?.length || b?.evidence?.length;

  return (
    <details className="group border-b border-line pb-3 [&_summary]:list-none">
      <summary className={hasDetail ? "cursor-pointer" : "cursor-default"}>
        <div className="mb-1.5 flex items-baseline justify-between gap-3">
          <span className="font-mono text-[0.64rem] uppercase tracking-widest2 text-muted">
            {label}
            {hasDetail ? (
              <span className="ml-2 text-faint opacity-0 transition-opacity group-hover:opacity-100 group-open:opacity-100">
                ▾
              </span>
            ) : null}
          </span>
          <span className="font-mono text-[0.66rem]">
            <span className="text-gold">{av}</span>
            <span className="text-faint"> / </span>
            <span className="text-ember">{bv}</span>
            <span className="ml-2 text-faint">
              {lead === "even" ? "·" : `Δ${Math.abs(delta)} → ${lead}`}
            </span>
          </span>
        </div>
        <MiniBar value={av} max={10} color={A} />
        <div className="h-1" />
        <MiniBar value={bv} max={10} color={B} />
      </summary>
      {hasDetail ? (
        <div className="mt-4 grid gap-5 md:grid-cols-2">
          <ScoreDetail data={a} name={aName} dot={A} />
          <ScoreDetail data={b} name={bName} dot={B} />
        </div>
      ) : null}
    </details>
  );
}

function ScoreDetail({ data, name, dot }: { data?: ArchetypeScore; name: string; dot: string }) {
  if (!data) return <div className="font-mono text-[0.7rem] text-faint">No data.</div>;
  return (
    <div>
      <div className="mb-2 flex items-center gap-2">
        <span className="inline-block h-2 w-2 rounded-full" style={{ background: dot }} />
        <span className="label text-faint">
          {name} · {data.score}/10{data.confidence ? ` · ${data.confidence}` : ""}
        </span>
      </div>
      {data.rationale ? (
        <p className="mb-3 font-mono text-[0.7rem] leading-relaxed text-muted">{data.rationale}</p>
      ) : null}
      {data.evidence?.length ? (
        <div className="space-y-3">
          {data.evidence.slice(0, 2).map((e, i) => (
            <Quote key={i} evidence={e} />
          ))}
        </div>
      ) : null}
    </div>
  );
}

/* --------------------------------------------------------------- typology */

function TypologyCol({ profile }: { profile: CompareModel["profile"] }) {
  const t = profile.typological_profile;
  if (!t) return <p className="font-mono text-[0.72rem] text-faint">No typology synthesized.</p>;
  const fns: Array<[string, string | undefined]> = [
    ["dominant", t.dominant_function],
    ["auxiliary", t.auxiliary_function],
    ["attitude", t.attitude],
    ["inferior", t.inferior_function],
  ];
  return (
    <div>
      <div className="grid grid-cols-2 gap-2">
        {fns.map(([k, v]) =>
          v ? (
            <div key={k} className="rounded-sm border border-line bg-void/30 px-3 py-2">
              <div className="label mb-0.5">{k}</div>
              <div className="font-serif text-[0.98rem] text-gold">{firstClause(v)}</div>
            </div>
          ) : null,
        )}
      </div>
      {t.rationale ? (
        <p className="mt-4 font-mono text-[0.7rem] leading-relaxed text-muted">{t.rationale}</p>
      ) : null}
    </div>
  );
}

// Function strings are often "Thinking — long rationale"; keep the headline.
function firstClause(s: string): string {
  return s.split(/[—(]/)[0].trim() || s;
}

/* --------------------------------------------------------------- topology */

function TopologyCol({ profile }: { profile: CompareModel["profile"] }) {
  const topo = profile.kerberos_topology;
  if (!topo) return <p className="font-mono text-[0.72rem] text-faint">No topology synthesized.</p>;
  return (
    <div className="space-y-5">
      <div className="space-y-px overflow-hidden rounded-sm border border-line">
        {(topo.domains_guarded ?? []).map((d, i) => (
          <div key={i} className="bg-void/30 p-4">
            <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2">
              <h4 className="font-serif text-base text-ink">{d.domain}</h4>
              <IntensityDots value={d.intensity} />
            </div>
            {d.activation_style ? (
              <p className="font-mono text-[0.68rem] leading-relaxed text-muted">{d.activation_style}</p>
            ) : null}
          </div>
        ))}
      </div>
      {topo.proportionality ? (
        <div>
          <div className="label mb-1">Proportionality</div>
          <p className="font-mono text-[0.7rem] leading-relaxed text-muted">{topo.proportionality}</p>
        </div>
      ) : null}
      {topo.gaps ? (
        <div>
          <div className="label mb-1">Where the dog sleeps</div>
          <p className="font-mono text-[0.7rem] leading-relaxed text-muted">{topo.gaps}</p>
        </div>
      ) : null}
    </div>
  );
}

/* ---------------------------------------------------------------- complex */

function ComplexCol({ profile }: { profile: CompareModel["profile"] }) {
  const complexes = profile.complex_map ?? [];
  if (!complexes.length) return <p className="font-mono text-[0.72rem] text-faint">No complexes mapped.</p>;
  return (
    <div className="space-y-px overflow-hidden rounded-sm border border-line">
      {complexes.map((c, i) => (
        <div key={i} className="bg-void/30 p-4">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <h4 className="font-serif text-base text-ink">{c.trigger_domain}</h4>
            <IntensityDots value={c.intensity} />
          </div>
          {c.activation_signature ? (
            <p className="mb-1 font-mono text-[0.68rem] leading-relaxed text-muted">
              <span className="text-faint">signature — </span>
              {spacedPipes(c.activation_signature)}
            </p>
          ) : null}
          {c.kerberos_involvement ? (
            <p className="font-mono text-[0.68rem] leading-relaxed text-muted">
              <span className="text-faint">kerberos — </span>
              {spacedPipes(c.kerberos_involvement)}
            </p>
          ) : null}
        </div>
      ))}
    </div>
  );
}

