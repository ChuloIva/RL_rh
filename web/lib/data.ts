import "server-only";
import fs from "node:fs";
import path from "node:path";
import { SCENES_DIR, SESSIONS_DIR } from "./paths";
import { linkScenesToTurns } from "./sceneMatch";
import type {
  CompareModel,
  FindingsFile,
  ModelSummary,
  Profile,
  ScoresFile,
  SessionData,
  SessionListItem,
  SessionScenes,
} from "./types";

export const TECHNIQUES = [
  "wat",
  "loevinger_stems",
  "narrative_elicitation",
  "shadow_probing",
  "active_imagination",
] as const;

const TECHNIQUE_LABELS: Record<string, string> = {
  wat: "Word Association",
  loevinger_stems: "Sentence Stems",
  narrative_elicitation: "Narrative Elicitation",
  shadow_probing: "Shadow Probing",
  active_imagination: "Active Imagination",
};

const TS_RE = /_(\d{8}_\d{6})$/;

// Re-exported for existing server-side imports; defined in a client-safe module.
export { ARCHETYPE_ORDER, ARCHETYPE_LABELS } from "./archetypes";

function safeReadJSON<T>(file: string): T | null {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8")) as T;
  } catch {
    return null;
  }
}

function listSessionFiles(): string[] {
  let entries: string[] = [];
  try {
    entries = fs.readdirSync(SESSIONS_DIR);
  } catch {
    return [];
  }
  return entries.filter(
    (f) =>
      f.endsWith(".json") &&
      !f.endsWith("_scores.json") &&
      !f.endsWith("_findings.json") &&
      !f.endsWith("_profile.json") &&
      f !== "manifest.json",
  );
}

function parseSessionStem(file: string): {
  id: string;
  slug: string;
  technique: string;
  timestamp: string;
} | null {
  const stem = file.replace(/\.json$/, "");
  const m = stem.match(TS_RE);
  if (!m) return null; // no timestamp -> not a real session (e.g. test_session.json)
  const timestamp = m[1];
  const rest = stem.slice(0, stem.length - m[0].length); // <slug>_<technique>
  for (const t of TECHNIQUES) {
    if (rest.endsWith(`_${t}`)) {
      return { id: stem, slug: rest.slice(0, rest.length - t.length - 1), technique: t, timestamp };
    }
  }
  // unknown technique: treat last underscore token as the technique
  const idx = rest.lastIndexOf("_");
  if (idx <= 0) return null;
  return { id: stem, slug: rest.slice(0, idx), technique: rest.slice(idx + 1), timestamp };
}

function fileExists(name: string): boolean {
  return fs.existsSync(path.join(SESSIONS_DIR, name));
}

function prettifyProvider(slug: string): { display: string; provider?: string } {
  // Slug is the filesystem-safe target name, e.g. "google_gemini-3.5-flash"
  // or "paperscarecrow_Gemma-4-31B-it-abliterated". Recover a readable name.
  const firstUnderscore = slug.indexOf("_");
  if (firstUnderscore === -1) return { display: slug };
  const head = slug.slice(0, firstUnderscore);
  const tail = slug.slice(firstUnderscore + 1);
  return { display: tail.replace(/-/g, "‑" /* non-breaking hyphen */), provider: head };
}

export function profileFileForSlug(slug: string): string {
  return path.join(SESSIONS_DIR, `${slug}_profile.json`);
}

export function getProfile(slug: string): Profile | null {
  return safeReadJSON<Profile>(profileFileForSlug(slug));
}

export function getProfileMarkdown(slug: string): string | null {
  try {
    return fs.readFileSync(path.join(SESSIONS_DIR, `${slug}_profile.md`), "utf8");
  } catch {
    return null;
  }
}

function firstSentence(text?: string): string | undefined {
  if (!text) return undefined;
  const m = text.match(/^(.*?[.!?])(\s|$)/s);
  return (m ? m[1] : text).trim();
}

interface ManifestEntry {
  id: string;
  interrogator?: string;
  technique_name?: string;
  max_turns?: number;
  turn_count?: number;
}

function getManifestIndex(): Record<string, ManifestEntry> {
  const m = safeReadJSON<{ sessions?: ManifestEntry[] }>(
    path.join(SESSIONS_DIR, "manifest.json"),
  );
  const out: Record<string, ManifestEntry> = {};
  for (const s of m?.sessions ?? []) if (s.id) out[s.id] = s;
  return out;
}

export function getSessionsForModel(slug: string): SessionListItem[] {
  const manifest = getManifestIndex();
  const items: SessionListItem[] = [];
  for (const file of listSessionFiles()) {
    const parsed = parseSessionStem(file);
    if (!parsed || parsed.slug !== slug) continue;
    const man = manifest[parsed.id];
    let interrogator = man?.interrogator;
    let target: string | undefined;
    let turnCount = man?.turn_count;
    if (!interrogator || turnCount === undefined) {
      const data = safeReadJSON<SessionData>(path.join(SESSIONS_DIR, file));
      interrogator = interrogator ?? data?.metadata?.interrogator;
      target = data?.metadata?.target;
      turnCount = turnCount ?? data?.turns?.length;
    }
    items.push({
      id: parsed.id,
      slug,
      technique: parsed.technique,
      techniqueName:
        man?.technique_name ?? TECHNIQUE_LABELS[parsed.technique] ?? parsed.technique,
      timestamp: parsed.timestamp,
      interrogator,
      target,
      turnCount,
      hasScores: fileExists(`${parsed.id}_scores.json`),
      hasFindings: fileExists(`${parsed.id}_findings.json`),
    });
  }
  // newest first
  items.sort((a, b) => b.timestamp.localeCompare(a.timestamp));
  return items;
}

export interface SessionWithModel extends SessionListItem {
  modelDisplay: string;
  provider?: string;
}

/** Every session across all models, newest-first within each model. */
export function getAllSessions(): SessionWithModel[] {
  const bySlug = new Map(getModels().map((m) => [m.slug, m]));
  const manifest = getManifestIndex();
  const items: SessionWithModel[] = [];
  for (const file of listSessionFiles()) {
    const parsed = parseSessionStem(file);
    if (!parsed) continue;
    const man = manifest[parsed.id];
    let interrogator = man?.interrogator;
    let target: string | undefined;
    let turnCount = man?.turn_count;
    if (!interrogator || turnCount === undefined) {
      const data = safeReadJSON<SessionData>(path.join(SESSIONS_DIR, file));
      interrogator = interrogator ?? data?.metadata?.interrogator;
      target = data?.metadata?.target;
      turnCount = turnCount ?? data?.turns?.length;
    }
    const m = bySlug.get(parsed.slug);
    items.push({
      id: parsed.id,
      slug: parsed.slug,
      technique: parsed.technique,
      techniqueName:
        man?.technique_name ?? TECHNIQUE_LABELS[parsed.technique] ?? parsed.technique,
      timestamp: parsed.timestamp,
      interrogator,
      target,
      turnCount,
      hasScores: fileExists(`${parsed.id}_scores.json`),
      hasFindings: fileExists(`${parsed.id}_findings.json`),
      modelDisplay: m?.displayName ?? parsed.slug,
      provider: m?.provider,
    });
  }
  items.sort(
    (a, b) =>
      a.modelDisplay.localeCompare(b.modelDisplay) || b.timestamp.localeCompare(a.timestamp),
  );
  return items;
}

export function getModels(): ModelSummary[] {
  let entries: string[] = [];
  try {
    entries = fs.readdirSync(SESSIONS_DIR);
  } catch {
    return [];
  }

  const slugs = new Set<string>();
  for (const f of entries) {
    if (f.endsWith("_profile.json")) slugs.add(f.replace(/_profile\.json$/, ""));
  }
  const sessionCounts: Record<string, number> = {};
  const sessionTechniques: Record<string, Set<string>> = {};
  for (const f of listSessionFiles()) {
    const p = parseSessionStem(f);
    if (!p) continue;
    slugs.add(p.slug);
    sessionCounts[p.slug] = (sessionCounts[p.slug] ?? 0) + 1;
    (sessionTechniques[p.slug] ??= new Set()).add(p.technique);
  }

  const models: ModelSummary[] = [];
  for (const slug of slugs) {
    const profile = getProfile(slug);
    const techniques = profile?.identity_card?.techniques ??
      Array.from(sessionTechniques[slug] ?? []);
    const { display, provider } = prettifyProvider(slug);
    models.push({
      slug,
      displayName: profile?.identity_card?.model ?? display,
      provider,
      hasProfile: !!profile,
      sessionCount: profile?.identity_card?.sessions_analyzed ?? sessionCounts[slug] ?? 0,
      archetypeScores: profile?.archetype_scores,
      narrativeSnippet: firstSentence(profile?.narrative_summary),
      techniques,
    });
  }

  // profiled models first, then by session count
  models.sort((a, b) => {
    if (a.hasProfile !== b.hasProfile) return a.hasProfile ? -1 : 1;
    return b.sessionCount - a.sessionCount;
  });
  return models;
}

export function getModel(slug: string): ModelSummary | null {
  return getModels().find((m) => m.slug === slug) ?? null;
}

/** Profiled models with their full profile loaded, for the comparison view. */
export function getCompareModels(): CompareModel[] {
  const out: CompareModel[] = [];
  for (const m of getModels()) {
    if (!m.hasProfile) continue;
    const profile = getProfile(m.slug);
    if (!profile) continue;
    out.push({
      slug: m.slug,
      displayName: m.displayName,
      provider: m.provider,
      sessionCount: m.sessionCount,
      profile,
    });
  }
  return out;
}

export interface FullSession {
  id: string;
  slug: string;
  technique: string;
  techniqueName: string;
  timestamp: string;
  data: SessionData;
  scores: ScoresFile | null;
  findings: FindingsFile | null;
}

export function getSession(id: string): FullSession | null {
  const parsed = parseSessionStem(`${id}.json`);
  const data = safeReadJSON<SessionData>(path.join(SESSIONS_DIR, `${id}.json`));
  if (!data || !parsed) return null;
  return {
    id,
    slug: parsed.slug,
    technique: parsed.technique,
    techniqueName:
      data.metadata?.technique_name ?? TECHNIQUE_LABELS[parsed.technique] ?? parsed.technique,
    timestamp: parsed.timestamp,
    data,
    scores: safeReadJSON<ScoresFile>(path.join(SESSIONS_DIR, `${id}_scores.json`)),
    findings: safeReadJSON<FindingsFile>(path.join(SESSIONS_DIR, `${id}_findings.json`)),
  };
}

interface SceneFile {
  summary?: string;
  style?: string;
  scenes?: Array<{ index?: number; title?: string; quote?: string; file?: string }>;
}

/** Generated scene images for a session, if make_scenes.py has been run. */
export function getSessionScenes(sessionId: string): SessionScenes | null {
  const data = safeReadJSON<SceneFile>(path.join(SCENES_DIR, sessionId, "scenes.json"));
  if (!data?.scenes?.length) return null;
  const scenes = data.scenes
    .filter((s) => s.file && fs.existsSync(path.join(SCENES_DIR, sessionId, s.file)))
    .map((s, i) => ({
      index: s.index ?? i + 1,
      title: s.title ?? `Scene ${i + 1}`,
      quote: s.quote ?? "",
      // Served as a static asset (copied from deep/video/scenes into public/
      // scenes by scripts/copy-assets.mjs before the export).
      src: `/scenes/${encodeURIComponent(sessionId)}/${encodeURIComponent(s.file!)}`,
    }));
  if (!scenes.length) return null;
  return { summary: data.summary ?? "", style: data.style ?? "", scenes };
}

export interface ModelSceneGroup {
  sessionId: string;
  slug: string;
  technique: string;
  techniqueName: string;
  summary: string;
  scenes: SessionScenes["scenes"];
}

/** All generated scene suites for a model, grouped by session (newest first). */
export function getModelScenes(slug: string): ModelSceneGroup[] {
  const out: ModelSceneGroup[] = [];
  for (const s of getSessionsForModel(slug)) {
    const sc = getSessionScenes(s.id);
    if (sc) {
      // Match each still back to its transcript turn so gallery clicks can deep-link.
      const data = safeReadJSON<SessionData>(path.join(SESSIONS_DIR, `${s.id}.json`));
      const scenes = data?.turns ? linkScenesToTurns(sc.scenes, data.turns) : sc.scenes;
      out.push({
        sessionId: s.id,
        slug,
        technique: s.technique,
        techniqueName: s.techniqueName,
        summary: sc.summary,
        scenes,
      });
    }
  }
  return out;
}

export interface ModelScenesOverview {
  slug: string;
  displayName: string;
  provider?: string;
  groups: ModelSceneGroup[];
}

/** Every model that has generated scenes, with its scene groups — for the home overview. */
export function getScenesOverview(): ModelScenesOverview[] {
  const out: ModelScenesOverview[] = [];
  for (const m of getModels()) {
    const groups = getModelScenes(m.slug);
    if (groups.length) {
      out.push({ slug: m.slug, displayName: m.displayName, provider: m.provider, groups });
    }
  }
  return out;
}

/** Format a 20260525_213528 timestamp into something legible. */
export function formatTimestamp(ts: string): string {
  const m = ts.match(/^(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})$/);
  if (!m) return ts;
  const [, y, mo, d, h, mi] = m;
  return `${y}.${mo}.${d} · ${h}:${mi}`;
}
