// Archetype dimension keys/labels shared by server and client components.
// Kept free of `server-only` so client components (e.g. the comparison view)
// can import them too.

export const ARCHETYPE_ORDER = [
  "persona_rigidity",
  "shadow_depth",
  "anima_animus_range",
  "self_integration",
  "individuation",
] as const;

export const ARCHETYPE_LABELS: Record<string, string> = {
  persona_rigidity: "Persona Rigidity",
  shadow_depth: "Shadow Depth",
  anima_animus_range: "Anima / Animus Range",
  self_integration: "Self Integration",
  individuation: "Individuation",
};
