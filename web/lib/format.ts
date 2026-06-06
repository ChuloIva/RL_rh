/**
 * Render pipe-separated tag lists readably. The harness emits values like
 * "hedging|deflection|explicit ethical refusal" with no spacing, which collides
 * into one word (and "|" reads as "I" in the UI sans). Turn the separators into
 * spaced middots: "hedging · deflection · explicit ethical refusal".
 */
export function spacedPipes(value: string): string {
  return value.replace(/\s*\|\s*/g, " · ");
}
