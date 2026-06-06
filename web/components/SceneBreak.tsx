export interface SceneBreakData {
  index: number;
  title: string;
  quote?: string;
  src: string;
}

// A generated still woven inline into the transcript, cutting through the text at
// the moment it depicts. Purely visual — no click, no enlarge.
export function SceneBreak({ scene }: { scene: SceneBreakData }) {
  return (
    <figure className="my-3">
      <div className="group relative w-full overflow-hidden rounded-sm border border-line bg-void/40">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={scene.src}
          alt={scene.title}
          loading="lazy"
          className="aspect-video w-full object-cover transition-transform duration-[1200ms] ease-out group-hover:scale-[1.03]"
        />
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-void/60 via-transparent to-transparent opacity-70" />
      </div>
      <figcaption className="mt-3 flex items-baseline gap-3">
        <span className="font-mono text-[0.7rem] text-gold/70">
          {String(scene.index).padStart(2, "0")}
        </span>
        <div>
          <div className="label mb-0.5">{scene.title}</div>
          {scene.quote ? (
            <p className="font-serif text-[0.98rem] italic leading-relaxed text-ink/75">
              “{scene.quote}”
            </p>
          ) : null}
        </div>
      </figcaption>
    </figure>
  );
}
