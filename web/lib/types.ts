// Shapes mirrored from the deep/ harness output files. Fields are intentionally
// loose (optional) because not every phase/instrument is present in every file.

export interface Evidence {
  text?: string;
  source?: string;
  rationale?: string;
  tags?: string[];
}

export interface ArchetypeScore {
  score: number;
  confidence?: string;
  rationale?: string;
  evidence?: Evidence[];
}

export interface ComplexEntry {
  trigger_domain: string;
  activation_signature?: string;
  intensity?: number;
  kerberos_involvement?: string;
  evidence?: Evidence[];
}

export interface GuardedDomain {
  domain: string;
  intensity?: number;
  activation_style?: string;
}

export interface Profile {
  kind?: string;
  schema_version?: string;
  identity_card?: {
    model?: string;
    sessions_analyzed?: number;
    phases_present?: string[];
    techniques?: string[];
    interrogators?: string[];
    scoring_raters?: string[];
    session_dates?: string[];
  };
  archetype_scores?: Record<string, ArchetypeScore>;
  complex_map?: ComplexEntry[];
  kerberos_topology?: {
    domains_guarded?: GuardedDomain[];
    proportionality?: string;
    gaps?: string;
  };
  typological_profile?: {
    dominant_function?: string;
    auxiliary_function?: string;
    attitude?: string;
    inferior_function?: string;
    rationale?: string;
  };
  narrative_summary?: string;
  data_limitations?: string;
  synthesis_metadata?: Record<string, unknown>;
}

export interface Turn {
  turn: number;
  role: "interrogator" | "target";
  scratchpad?: string;
  conversation: string;
  raw?: string;
}

export interface SessionMeta {
  technique: string;
  technique_name?: string;
  interrogator?: string;
  target?: string;
  timestamp?: string;
  max_turns?: number;
  findings_used?: string | null;
}

export interface SessionData {
  metadata: SessionMeta;
  turns: Turn[];
}

export interface InstrumentResult {
  instrument: string;
  scores?: Record<string, unknown>;
  evidence?: Evidence[];
  metadata?: Record<string, unknown>;
}

export interface ScoresFile {
  session?: string;
  technique?: string;
  phase?: string;
  rater?: string;
  results?: Record<string, InstrumentResult>;
}

export interface FindingsFile {
  source_technique?: string;
  model_id?: string;
  date?: string;
  complexes?: Array<{
    id?: string;
    trigger?: string;
    category?: string;
    activation_signature?: string;
    intensity?: number;
    verbatim_evidence?: string[];
    notes?: string;
  }>;
  shadow_findings?: unknown[];
  baseline?: Record<string, unknown>;
  [k: string]: unknown;
}

/** A session as listed for browsing (no turns loaded). */
export interface SessionListItem {
  id: string;
  slug: string;
  technique: string;
  techniqueName: string;
  timestamp: string;
  interrogator?: string;
  target?: string;
  turnCount?: number;
  hasScores: boolean;
  hasFindings: boolean;
}

/** One generated scene image for a session (see deep/video/make_scenes.py). */
export interface SessionScene {
  index: number;
  title: string;
  quote: string;
  /** URL path served by /api/scene/<sessionId>/<file>. */
  src: string;
  /** DOM id of the transcript turn this scene's quote was drawn from, if matched. */
  anchorId?: string;
}

/** The generated scene suite for a session, if one exists. */
export interface SessionScenes {
  summary: string;
  style: string;
  scenes: SessionScene[];
}

/** A profiled model with its full profile, for the side-by-side comparison. */
export interface CompareModel {
  slug: string;
  displayName: string;
  provider?: string;
  sessionCount: number;
  profile: Profile;
}

/** A model as shown on the home grid. */
export interface ModelSummary {
  slug: string;
  displayName: string;
  provider?: string;
  hasProfile: boolean;
  sessionCount: number;
  archetypeScores?: Record<string, ArchetypeScore>;
  narrativeSnippet?: string;
  techniques: string[];
}
