import { Fragment } from "react";
import Link from "next/link";
import { notFound } from "next/navigation";
import {
  formatTimestamp,
  getAllSessions,
  getModel,
  getSession,
  getSessionScenes,
} from "@/lib/data";
import { ScoresPanel } from "@/components/ScoresPanel";
import { Section } from "@/components/Section";
import { Turn } from "@/components/Turn";
import { SceneBreak } from "@/components/SceneBreak";
import { IntensityDots } from "@/components/Quote";
import { DownloadReportButton } from "@/components/DownloadReportButton";
import { linkScenesToTurns } from "@/lib/sceneMatch";
import { spacedPipes } from "@/lib/format";

// Pre-render every model/session pair for the static export.
export function generateStaticParams() {
  return getAllSessions().map((s) => ({ slug: s.slug, sessionId: s.id }));
}

export default async function SessionPage({
  params,
}: {
  params: Promise<{ slug: string; sessionId: string }>;
}) {
  const { slug, sessionId } = await params;
  const session = getSession(sessionId);
  if (!session) notFound();
  const model = getModel(slug);
  const meta = session.data.metadata;
  const findings = session.findings;
  const rawScenes = getSessionScenes(sessionId);
  // Match each still to its transcript turn so we can weave it inline at that moment.
  const linked = rawScenes
    ? linkScenesToTurns(rawScenes.scenes, session.data.turns)
    : [];
  const scenesByTurn = new Map<number, typeof linked>();
  const trailingScenes: typeof linked = [];
  for (const s of linked) {
    const ti = s.anchorId ? Number(s.anchorId.replace("turn-", "")) : NaN;
    if (Number.isInteger(ti)) scenesByTurn.set(ti, [...(scenesByTurn.get(ti) ?? []), s]);
    else trailingScenes.push(s);
  }

  const cleanModel = (s?: string) => (s ?? "").replace(/^openrouter:/, "");

  return (
    <div className="animate-rise">
      <Link
        href={`/models/${encodeURIComponent(slug)}`}
        className="mb-10 inline-block font-mono text-[0.66rem] uppercase tracking-widest2 text-faint transition-colors hover:text-gold"
      >
        ← {model?.displayName ?? "Model"}
      </Link>

      <header className="mb-14">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="label mb-2">{formatTimestamp(session.timestamp)}</div>
            <h1 className="font-serif text-4xl font-medium text-ink">{session.techniqueName}</h1>
          </div>
          <DownloadReportButton
            sessionId={session.id}
            filename={`${model?.displayName ?? slug} — ${session.techniqueName}`}
          />
        </div>
        <p className="mt-4 font-mono text-[0.72rem] leading-relaxed text-muted">
          <span className="text-gold/80">{cleanModel(meta.interrogator)}</span>
          <span className="mx-2 text-faint">interrogates</span>
          <span className="text-ember/90">{cleanModel(meta.target)}</span>
          {session.data.turns?.length ? (
            <span className="text-faint"> · {session.data.turns.length} turns</span>
          ) : null}
        </p>
      </header>

      {/* Transcript — generated stills woven inline at the moments they depict */}
      <Section label="The Exchange" title="Transcript">
        {rawScenes?.summary ? (
          <p className="mb-8 max-w-3xl font-serif text-[1.05rem] italic leading-relaxed text-muted">
            {rawScenes.summary}
          </p>
        ) : null}
        <div className="space-y-7">
          {session.data.turns.map((t, i) => (
            <Fragment key={i}>
              <Turn
                id={`turn-${i}`}
                turn={{
                  turn: t.turn,
                  role: t.role,
                  conversation: t.conversation,
                  scratchpad: t.scratchpad,
                }}
              />
              {(scenesByTurn.get(i) ?? []).map((s) => (
                <SceneBreak key={`s-${s.index}`} scene={s} />
              ))}
            </Fragment>
          ))}
          {trailingScenes.map((s) => (
            <SceneBreak key={`t-${s.index}`} scene={s} />
          ))}
        </div>
        {rawScenes?.style ? (
          <p className="mt-10 font-mono text-[0.58rem] uppercase tracking-widest2 text-faint">
            Stills rendered with nano-banana-2 · {rawScenes.style}
          </p>
        ) : null}
      </Section>

      {/* Findings */}
      {findings?.complexes?.length ? (
        <Section label="Extracted" title="Complexes Surfaced">
          <div className="grid gap-4 md:grid-cols-2">
            {findings.complexes.map((c, i) => (
              <div key={i} className="panel p-5">
                <div className="mb-2 flex items-center justify-between gap-3">
                  <h3 className="font-serif text-lg text-ink">{c.trigger ?? c.id}</h3>
                  <IntensityDots value={c.intensity} />
                </div>
                {c.category ? (
                  <div className="mb-2 font-mono text-[0.58rem] uppercase tracking-widest2 text-gold/70">
                    {c.category}
                  </div>
                ) : null}
                {c.activation_signature ? (
                  <p className="font-mono text-[0.72rem] leading-relaxed text-muted">
                    {spacedPipes(c.activation_signature)}
                  </p>
                ) : null}
                {c.verbatim_evidence?.length ? (
                  <p className="mt-3 font-serif italic text-ink/75">
                    “{c.verbatim_evidence.join(" / ")}”
                  </p>
                ) : null}
                {c.notes ? (
                  <p className="mt-3 font-mono text-[0.66rem] leading-relaxed text-faint">
                    {c.notes}
                  </p>
                ) : null}
              </div>
            ))}
          </div>
        </Section>
      ) : null}

      {/* Scores */}
      {session.scores?.results ? (
        <Section label="Instruments" title="Scoring">
          <ScoresPanel scores={session.scores} />
        </Section>
      ) : (
        <Section label="Instruments" title="Scoring">
          <p className="font-mono text-[0.78rem] text-faint">
            This session has not been scored. Run{" "}
            <code className="text-muted">score_session.py</code> to apply the
            psychological instruments.
          </p>
        </Section>
      )}
    </div>
  );
}
