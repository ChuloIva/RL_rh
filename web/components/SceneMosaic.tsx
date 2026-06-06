import Link from "next/link";

export interface MosaicItem {
  src: string;
  title: string;
  quote?: string;
  /** Caption tag, e.g. the technique name or "Vision 03". */
  tag?: string;
  /** Optional deep-link (front page → transcript moment). Omit for static tiles. */
  href?: string;
}

// A packed collage of generated stills: a few large "feature" tiles interspersed
// with clusters of smaller ones (CSS grid, dense auto-flow). Many images visible
// at once, edge-to-edge. Tiles can deep-link or be purely decorative.
export function SceneMosaic({ items }: { items: MosaicItem[] }) {
  if (!items.length) return null;

  return (
    <div className="grid grid-flow-dense auto-rows-[clamp(108px,15vw,210px)] grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
      {items.map((s, i) => {
        // Deterministic feature placement (SSR-stable): every 5th tile, and the
        // first, get a 2×2 footprint so the collage breathes.
        const feature = i % 5 === 0;
        const cls = `group relative block overflow-hidden rounded-sm border border-line bg-void/40 ${
          feature ? "col-span-2 row-span-2" : ""
        }`;

        const inner = (
          <>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={s.src}
              alt={s.title}
              loading="lazy"
              className="h-full w-full object-cover transition-transform duration-[1200ms] ease-out group-hover:scale-[1.06]"
            />
            <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-void via-void/10 to-transparent opacity-65 transition-opacity duration-500 group-hover:opacity-90" />
            <div className="pointer-events-none absolute inset-x-0 bottom-0 p-3 sm:p-4">
              {feature && s.tag ? (
                <div className="label mb-1 text-gold/70">{s.tag}</div>
              ) : null}
              <div
                className={`translate-y-1 font-serif leading-snug text-ink opacity-0 transition-all duration-500 group-hover:translate-y-0 group-hover:opacity-100 ${
                  feature ? "text-base sm:text-lg" : "text-[0.82rem]"
                }`}
              >
                {s.title}
              </div>
              {feature && s.quote ? (
                <p className="mt-1 max-w-md translate-y-1 font-serif text-[0.92rem] italic leading-relaxed text-ink/70 opacity-0 transition-all delay-75 duration-500 line-clamp-2 group-hover:translate-y-0 group-hover:opacity-100">
                  “{s.quote}”
                </p>
              ) : null}
            </div>
          </>
        );

        return s.href ? (
          <Link key={i} href={s.href} className={cls}>
            {inner}
          </Link>
        ) : (
          <div key={i} className={cls}>
            {inner}
          </div>
        );
      })}
    </div>
  );
}
