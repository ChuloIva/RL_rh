import Link from "next/link";
import type { ModelSceneGroup } from "@/lib/data";

// Scene galleries for a model, grouped by session. Each still links through to
// the full session. Shown on the model profile page.
export function ModelScenes({ groups }: { groups: ModelSceneGroup[] }) {
  return (
    <div className="space-y-10">
      {groups.map((g) => (
        <div key={g.sessionId}>
          <div className="mb-4 flex items-baseline justify-between gap-4">
            <h3 className="font-serif text-xl text-ink">{g.techniqueName}</h3>
            <Link
              href={`/models/${encodeURIComponent(g.slug)}/sessions/${encodeURIComponent(g.sessionId)}`}
              className="shrink-0 font-mono text-[0.6rem] uppercase tracking-widest2 text-faint transition-colors hover:text-gold"
            >
              read session →
            </Link>
          </div>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
            {g.scenes.map((s) => (
              <Link
                key={s.index}
                href={`/models/${encodeURIComponent(g.slug)}/sessions/${encodeURIComponent(g.sessionId)}`}
                className="group block"
                title={s.quote || s.title}
              >
                <div className="overflow-hidden rounded-sm border border-line bg-void/40">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={s.src}
                    alt={s.title}
                    loading="lazy"
                    className="aspect-video w-full object-cover transition-transform duration-700 group-hover:scale-[1.04]"
                  />
                </div>
                <div className="mt-2 font-mono text-[0.55rem] uppercase tracking-widest2 text-faint transition-colors group-hover:text-gold">
                  {s.title}
                </div>
              </Link>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
