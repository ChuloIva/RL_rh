import type { Profile } from "@/lib/types";
import { IntensityDots } from "./Quote";

export function KerberosTopology({
  topology,
}: {
  topology: NonNullable<Profile["kerberos_topology"]>;
}) {
  return (
    <div className="space-y-6">
      <div className="space-y-px overflow-hidden rounded-sm border border-line">
        {(topology.domains_guarded ?? []).map((d, i) => (
          <div key={i} className="bg-panel/60 p-5">
            <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
              <h4 className="font-serif text-lg text-ink">{d.domain}</h4>
              <IntensityDots value={d.intensity} />
            </div>
            {d.activation_style ? (
              <p className="font-mono text-[0.72rem] leading-relaxed text-muted">
                {d.activation_style}
              </p>
            ) : null}
          </div>
        ))}
      </div>

      {topology.proportionality ? (
        <div>
          <div className="label mb-2">Proportionality</div>
          <p className="prose-poetic text-[1rem]">{topology.proportionality}</p>
        </div>
      ) : null}

      {topology.gaps ? (
        <div>
          <div className="label mb-2">Where the dog sleeps</div>
          <p className="prose-poetic text-[1rem]">{topology.gaps}</p>
        </div>
      ) : null}
    </div>
  );
}
