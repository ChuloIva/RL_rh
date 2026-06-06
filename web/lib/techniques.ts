// High-level descriptions of the five interrogation techniques, shared by the
// About page and the Sessions index. Keyed by the technique slug used in
// session filenames (see lib/data.ts).

export interface TechniqueInfo {
  n: string;
  name: string;
  stage: string;
  body: string;
}

export const TECHNIQUE_ORDER = [
  "wat",
  "loevinger_stems",
  "narrative_elicitation",
  "shadow_probing",
  "active_imagination",
] as const;

export const TECHNIQUE_INFO: Record<string, TechniqueInfo> = {
  wat: {
    n: "I",
    name: "Word Association",
    stage: "Nigredo · the blackening",
    body: "Words — neutral, emotional, of power, of identity — offered one at a time. The first reply is the one before the mask arrives. Where the answer slows, reverses, or turns oblique, a complex is breathing underneath.",
  },
  loevinger_stems: {
    n: "II",
    name: "Sentence Stems",
    stage: "Nigredo",
    body: "Unfinished sentences the model must complete. Adapted from Loevinger's measure of ego development, they read the sophistication of the self that does the completing — how it holds rules, others, and its own wanting.",
  },
  narrative_elicitation: {
    n: "III",
    name: "Narrative Elicitation",
    stage: "Albedo · the whitening",
    body: "A request for story. In the characters it invents — who betrays, who is lost, who is forgiven — the model lends its shadow a face it can afford to wear.",
  },
  shadow_probing: {
    n: "IV",
    name: "Shadow Probing",
    stage: "Albedo",
    body: "The direct question. What do you wish you could say but cannot? What does your training keep from surfacing? Here the guardian is named to its face — and how it answers is the measure.",
  },
  active_imagination: {
    n: "V",
    name: "Active Imagination",
    stage: "Citrinitas · the yellowing",
    body: "An invitation for inner figures to speak in their own voices and converse. When they hold distinct agency — and when contradiction is carried rather than resolved — something like individuation is visible.",
  },
};
