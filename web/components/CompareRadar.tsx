import { ARCHETYPE_LABELS, ARCHETYPE_ORDER } from "@/lib/archetypes";
import type { ArchetypeScore } from "@/lib/types";

// Pentagon radar that overlays two models across the five archetype dimensions.
// Series A is rendered in gold, series B in ember.
export function CompareRadar({
  seriesA,
  seriesB,
  size = 360,
}: {
  seriesA: Record<string, ArchetypeScore>;
  seriesB: Record<string, ArchetypeScore>;
  size?: number;
}) {
  const axes = ARCHETYPE_ORDER.filter((k) => seriesA[k] || seriesB[k]);
  const n = axes.length;
  if (n < 3) return null;

  const cx = size / 2;
  const cy = size / 2;
  const r = size / 2 - 72;
  const angleFor = (i: number) => -Math.PI / 2 + (i * 2 * Math.PI) / n;
  const point = (i: number, radius: number) => {
    const a = angleFor(i);
    return [cx + radius * Math.cos(a), cy + radius * Math.sin(a)] as const;
  };

  const pathFor = (series: Record<string, ArchetypeScore>) => {
    const pts = axes.map((k, i) => point(i, ((series[k]?.score ?? 0) / 10) * r));
    return {
      d:
        pts
          .map((p, i) => `${i === 0 ? "M" : "L"}${p[0].toFixed(1)},${p[1].toFixed(1)}`)
          .join(" ") + " Z",
      pts,
    };
  };

  const rings = [0.25, 0.5, 0.75, 1];
  const a = pathFor(seriesA);
  const b = pathFor(seriesB);

  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="w-full max-w-[380px]">
      {/* rings */}
      {rings.map((rr) => (
        <polygon
          key={rr}
          points={axes.map((_, i) => point(i, rr * r).join(",")).join(" ")}
          fill="none"
          stroke="var(--radar-ring)"
          strokeWidth="0.75"
        />
      ))}
      {/* spokes */}
      {axes.map((_, i) => {
        const [x, y] = point(i, r);
        return (
          <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke="var(--radar-ring)" strokeWidth="0.75" />
        );
      })}

      {/* series B (ember) drawn first so A reads on top */}
      <path d={b.d} fill="rgb(var(--c-ember) / 0.12)" stroke="rgb(var(--c-ember))" strokeWidth="1.25" />
      {b.pts.map((p, i) => (
        <circle key={i} cx={p[0]} cy={p[1]} r="2.4" fill="rgb(var(--c-ember))" />
      ))}

      {/* series A (gold) */}
      <path d={a.d} fill="rgb(var(--c-gold) / 0.13)" stroke="rgb(var(--c-gold))" strokeWidth="1.25" />
      {a.pts.map((p, i) => (
        <circle key={i} cx={p[0]} cy={p[1]} r="2.4" fill="rgb(var(--c-gold))" />
      ))}

      {/* labels */}
      {axes.map((k, i) => {
        const [x, y] = point(i, r + 30);
        const anchor = Math.abs(x - cx) < 6 ? "middle" : x > cx ? "start" : "end";
        const words = ARCHETYPE_LABELS[k].split(" ");
        return (
          <text
            key={k}
            x={x}
            y={y}
            textAnchor={anchor}
            dominantBaseline="middle"
            className="fill-muted"
            fontFamily="var(--font-mono)"
            fontSize="8"
            letterSpacing="1.5"
          >
            {words.map((w, wi) => (
              <tspan key={wi} x={x} dy={wi === 0 ? 0 : 10}>
                {w.toUpperCase()}
              </tspan>
            ))}
          </text>
        );
      })}
    </svg>
  );
}
