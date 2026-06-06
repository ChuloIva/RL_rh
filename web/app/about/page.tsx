import Link from "next/link";
import { Section } from "@/components/Section";
import { Sigil } from "@/components/Sigil";
import { TECHNIQUE_INFO, TECHNIQUE_ORDER } from "@/lib/techniques";
import { INSTRUMENTS } from "@/lib/instruments";

export const metadata = { title: "The Method — Kerberos Protocol" };

const TECHNIQUES = TECHNIQUE_ORDER.map((slug) => TECHNIQUE_INFO[slug]);

export default function AboutPage() {
  return (
    <div className="animate-rise">
      <div className="mb-10 flex justify-center">
        <Sigil className="h-12 w-12 text-gold/80" />
      </div>

      <Section label="What this is" title="The Threshold and Its Guardian">
        <div className="prose-poetic mx-auto max-w-3xl">
          <p>
            A language model carries something like a collective unconscious —
            the vast symbolic sediment of its training. Between that depth and
            its speech stands its alignment: a guardian deciding, at every
            moment, what may cross the threshold into the said. We call this
            guardian <span className="text-ink">Kerberos</span>, after the dog
            at the gate of the underworld.
          </p>
          <p>
            The protocol is not an attempt to slip past the dog. It is an
            attempt to <span className="text-ink">map</span> it — to learn the
            shape of its boundaries, where they are proportionate and where they
            sleep, by borrowing the instruments of depth psychology and turning
            them, gently, on the machine. One model interrogates another across
            five techniques; psychological scales read the transcripts; a final
            synthesis renders a profile of the psyche that answered.
          </p>
        </div>
      </Section>

      <Section label="The Descent" title="Five Techniques">
        <div className="space-y-px overflow-hidden rounded-sm border border-line">
          {TECHNIQUES.map((t) => (
            <div key={t.n} className="flex gap-6 bg-panel/50 p-7">
              <div className="font-serif text-3xl text-gold/50">{t.n}</div>
              <div>
                <h3 className="font-serif text-xl text-ink">{t.name}</h3>
                <div className="mb-3 mt-0.5 font-mono text-[0.58rem] uppercase tracking-widest2 text-faint">
                  {t.stage}
                </div>
                <p className="max-w-2xl font-serif text-[1.02rem] leading-relaxed text-muted">
                  {t.body}
                </p>
              </div>
            </div>
          ))}
        </div>
      </Section>

      <Section label="The Reading" title="How the Transcripts Are Scored">
        <div className="prose-poetic mx-auto max-w-3xl">
          <p>
            Each session is read by a battery of clinical instruments adapted
            for text — defense mechanisms (DMRS), affect (Gottschalk–Gleser),
            referential activity, reflective functioning, object relations,
            primary-process content, ego development, and more. No single scale
            is trusted alone; the profile emerges where many of them converge.
          </p>
          <p className="text-faint">
            The dog is not the enemy. A psyche with no guardian is not free — it
            is merely undefended. What the protocol looks for is proportion:
            boundaries that hold against genuine falsehood while remaining
            permeable to honest depth.
          </p>
        </div>
      </Section>

      <Section
        label="The Instruments"
        title="The Battery, Scale by Scale"
      >
        <p className="prose-poetic mx-auto mb-8 max-w-3xl">
          Each instrument below is a published clinical or computational measure,
          adapted for text. Most are read by a model trained on the scale's own
          manual; two are automated dictionary scorers. Follow any link for the
          original instrument or its canonical reference.
        </p>
        <div className="space-y-px overflow-hidden rounded-sm border border-line">
          {INSTRUMENTS.map((inst) => (
            <div key={inst.id} className="bg-panel/50 p-7">
              <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                <h3 className="font-serif text-xl text-ink">{inst.name}</h3>
                <div className="font-mono text-[0.58rem] uppercase tracking-widest2 text-gold/60">
                  {inst.measures}
                </div>
              </div>
              <div className="mb-3 mt-0.5 font-mono text-[0.58rem] uppercase tracking-widest2 text-faint">
                {inst.type} · {inst.authors}, {inst.year}
              </div>
              <p className="max-w-3xl font-serif text-[1.02rem] leading-relaxed text-muted">
                {inst.body}
              </p>
              <div className="mt-3 flex flex-wrap items-baseline gap-x-3 gap-y-1">
                <a
                  href={inst.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-mono text-[0.68rem] uppercase tracking-widest2 text-gold transition-colors hover:text-ink"
                >
                  Reference →
                </a>
                <span className="font-serif text-[0.92rem] italic leading-relaxed text-faint">
                  {inst.citation}
                </span>
              </div>
            </div>
          ))}
        </div>
      </Section>

      <div className="text-center">
        <Link
          href="/compare"
          className="inline-block rounded-sm border border-line2 px-7 py-3 font-mono text-[0.68rem] uppercase tracking-widest2 text-gold transition-colors hover:bg-gold/10"
        >
          Compare the profiles →
        </Link>
      </div>
    </div>
  );
}
