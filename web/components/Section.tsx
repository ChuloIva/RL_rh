import type { ReactNode } from "react";

export function Section({
  label,
  title,
  children,
  className = "",
}: {
  label?: string;
  title?: ReactNode;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <section className={`mb-16 ${className}`}>
      {label ? <div className="label mb-3">{label}</div> : null}
      {title ? (
        <h2 className="mb-6 font-serif text-[1.7rem] font-medium tracking-wide text-ink">
          {title}
        </h2>
      ) : null}
      {children}
    </section>
  );
}
