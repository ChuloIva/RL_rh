// Stages the large binary assets that live under ../deep into web/public so the
// Next.js static export (output: "export") bundles them into out/. Runs as the
// `prebuild` step, both locally and on Cloudflare Pages (root directory = web).
//
//   deep/video/scenes/<sessionId>/*.png  ->  public/scenes/<sessionId>/*.png
//   deep/reports/*.pdf                   ->  public/reports/*.pdf
//
// public/scenes and public/reports are git-ignored — the originals in deep/ are
// the committed source of truth.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const webRoot = path.join(here, "..");
const DEEP_DIR = process.env.DEEP_DIR ?? path.join(webRoot, "..", "deep");

const SCENES_SRC = path.join(DEEP_DIR, "video", "scenes");
const SCENES_DST = path.join(webRoot, "public", "scenes");
const REPORTS_SRC = path.join(DEEP_DIR, "reports");
const REPORTS_DST = path.join(webRoot, "public", "reports");

function copyScenes() {
  if (!fs.existsSync(SCENES_SRC)) {
    console.warn(`[copy-assets] no scenes dir at ${SCENES_SRC} — skipping`);
    return;
  }
  fs.rmSync(SCENES_DST, { recursive: true, force: true });
  fs.cpSync(SCENES_SRC, SCENES_DST, { recursive: true });
  const n = fs.readdirSync(SCENES_DST).length;
  console.log(`[copy-assets] scenes: ${n} session folders -> public/scenes`);
}

function copyReports() {
  if (!fs.existsSync(REPORTS_SRC)) {
    console.warn(`[copy-assets] no reports dir at ${REPORTS_SRC} — skipping`);
    return;
  }
  fs.mkdirSync(REPORTS_DST, { recursive: true });
  let n = 0;
  for (const f of fs.readdirSync(REPORTS_SRC)) {
    if (!f.endsWith(".pdf")) continue;
    fs.copyFileSync(path.join(REPORTS_SRC, f), path.join(REPORTS_DST, f));
    n++;
  }
  console.log(`[copy-assets] reports: ${n} PDFs -> public/reports`);
}

copyScenes();
copyReports();
