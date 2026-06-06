import path from "node:path";

/**
 * Root of the `deep/` harness. Under `npm run dev` the cwd is `web/`, so the
 * default resolves to the sibling `deep/`. Override with DEEP_DIR if running
 * the UI from elsewhere.
 */
export const DEEP_DIR =
  process.env.DEEP_DIR ?? path.join(process.cwd(), "..", "deep");

export const SESSIONS_DIR = path.join(DEEP_DIR, "sessions");
export const TECHNIQUES_DIR = path.join(DEEP_DIR, "techniques");
/** Generated scene images live under deep/video/scenes/<session_id>/. */
export const SCENES_DIR = path.join(DEEP_DIR, "video", "scenes");

/** Candidate python interpreters for the live runner — prefer a repo venv. */
export const PYTHON_CANDIDATES = [
  path.join(DEEP_DIR, "..", ".venv", "bin", "python"),
  path.join(DEEP_DIR, "..", "venv", "bin", "python"),
];
