/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export: every page is pre-rendered at build time (reading the data in
  // ../deep) and emitted to out/ as plain files, so the site can be hosted on
  // Cloudflare Pages with no Node server. See scripts/copy-assets.mjs, which
  // stages the scene images and PDF reports into public/ before the export.
  output: "export",
  // The export has no image optimization server; serve images as-is.
  images: { unoptimized: true },
  // Emit /sessions/index.html etc. so static hosts resolve clean URLs.
  trailingSlash: true,
};

export default nextConfig;
