// A minimal occult mark: the threshold circle, an inscribed descending triangle,
// and three points — the three heads of the guardian at the gate.
export function Sigil({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 48 48"
      fill="none"
      stroke="currentColor"
      strokeWidth="1"
      className={className}
      aria-hidden
    >
      <circle cx="24" cy="24" r="21" opacity="0.55" />
      <path d="M24 9 L39 33 L9 33 Z" opacity="0.8" />
      <circle cx="24" cy="9" r="2.1" fill="currentColor" stroke="none" />
      <circle cx="39" cy="33" r="2.1" fill="currentColor" stroke="none" />
      <circle cx="9" cy="33" r="2.1" fill="currentColor" stroke="none" />
      <line x1="24" y1="20" x2="24" y2="33" opacity="0.5" />
    </svg>
  );
}
