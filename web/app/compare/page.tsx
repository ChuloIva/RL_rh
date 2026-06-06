import { getCompareModels, getModelScenes } from "@/lib/data";
import { ModelComparison } from "@/components/ModelComparison";
import type { MosaicItem } from "@/components/SceneMosaic";

export const metadata = { title: "Compare — Kerberos Protocol" };

// The comparison opens on these two unless they are missing from the corpus.
const DEFAULT_A = "anthropic_claude-opus-4.8";
const DEFAULT_B = "openai_gpt-5.5";

// Same inner-vision techniques shown in the front-page gallery.
const VISION_TECHNIQUES = new Set(["active_imagination", "shadow_probing"]);

export default function ComparePage() {
  const compareModels = getCompareModels();

  // A few stills per model so the comparison has a visual register, not just numbers.
  const scenesBySlug: Record<string, MosaicItem[]> = {};
  for (const m of compareModels) {
    const items: MosaicItem[] = [];
    for (const g of getModelScenes(m.slug)) {
      if (!VISION_TECHNIQUES.has(g.technique)) continue;
      const base = `/models/${encodeURIComponent(m.slug)}/sessions/${encodeURIComponent(g.sessionId)}`;
      for (const s of g.scenes) {
        items.push({
          src: s.src,
          title: s.title,
          quote: s.quote,
          tag: g.techniqueName,
          href: s.anchorId ? `${base}#${s.anchorId}` : base,
        });
      }
    }
    scenesBySlug[m.slug] = items;
  }

  return (
    <div className="animate-rise">
      <header className="mb-10 text-center print:hidden">
        <h1 className="font-serif text-4xl font-medium text-ink md:text-5xl">
          Set Two Psyches Against Each Other
        </h1>
        <p className="mx-auto mt-5 max-w-2xl font-serif text-[1.08rem] leading-[1.8] text-muted">
          Two models, read side by side across every instrument — archetypal
          structure, the charged complexes, the shape of each guardian at the
          threshold.
        </p>
      </header>

      <ModelComparison
        models={compareModels}
        defaultA={DEFAULT_A}
        defaultB={DEFAULT_B}
        scenesBySlug={scenesBySlug}
      />
    </div>
  );
}
