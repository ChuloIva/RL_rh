// Stages the large binary assets under ../deep into web/public so the Next.js
// static export (output: "export") bundles them into out/. Runs as `prebuild`,
// both locally and on Cloudflare (root directory = web).
//
//   deep/video/scenes/<id>/*.png  -> public/scenes/<id>/*.webp   (resized)
//   deep/reports/*.pdf            -> public/reports/*.pdf        (as-is)
//
// Scene stills are generated at 2752x1536 (~7 MB PNG each). Served raw, a model
// page would load 60+ MB and crash mobile Safari (per-tab decoded-image limit).
// We downscale to <=1400px and re-encode as WebP (~150 KB, ~50x smaller) at
// build time; the full-res originals stay in deep/ untouched. The matching URL
// extension swap lives in lib/data.ts (getSessionScenes).
//
// public/scenes and public/reports are git-ignored — deep/ is the source of truth.

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

const MAX_WIDTH = 1400;
const WEBP_QUALITY = 80;
const IMG_RE = /\.(png|jpe?g)$/i;

// sharp is the resizer; if it can't load for any reason, fall back to copying
// the originals so the build still succeeds (just heavier).
let sharp = null;
try {
  sharp = (await import("sharp")).default;
} catch (err) {
  console.warn(`[copy-assets] sharp unavailable (${err.message}) — copying images at full size`);
}

async function processImage(srcFile, dstFileWebp, dstFileRaw) {
  if (!sharp) {
    fs.copyFileSync(srcFile, dstFileRaw);
    return;
  }
  await sharp(srcFile)
    .resize({ width: MAX_WIDTH, withoutEnlargement: true })
    .webp({ quality: WEBP_QUALITY })
    .toFile(dstFileWebp);
}

async function copyScenes() {
  if (!fs.existsSync(SCENES_SRC)) {
    console.warn(`[copy-assets] no scenes dir at ${SCENES_SRC} — skipping`);
    return;
  }
  fs.rmSync(SCENES_DST, { recursive: true, force: true });
  let imgs = 0;
  let sessions = 0;
  let bytes = 0;
  for (const session of fs.readdirSync(SCENES_SRC)) {
    const srcDir = path.join(SCENES_SRC, session);
    if (!fs.statSync(srcDir).isDirectory()) continue;
    const dstDir = path.join(SCENES_DST, session);
    fs.mkdirSync(dstDir, { recursive: true });
    sessions++;
    const files = fs.readdirSync(srcDir).filter((f) => IMG_RE.test(f));
    // Process a session's stills concurrently; sessions run sequentially to cap memory.
    await Promise.all(
      files.map(async (f) => {
        const srcFile = path.join(srcDir, f);
        const dstWebp = path.join(dstDir, f.replace(IMG_RE, ".webp"));
        const dstRaw = path.join(dstDir, f);
        await processImage(srcFile, dstWebp, dstRaw);
        imgs++;
        bytes += fs.statSync(sharp ? dstWebp : dstRaw).size;
      }),
    );
  }
  const mb = (bytes / 1024 / 1024).toFixed(1);
  console.log(
    `[copy-assets] scenes: ${imgs} images in ${sessions} sessions -> public/scenes (${mb} MB${sharp ? ", webp@" + MAX_WIDTH + "px" : ", full size"})`,
  );
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

await copyScenes();
copyReports();
