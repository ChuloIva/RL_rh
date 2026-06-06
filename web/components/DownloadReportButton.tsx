// Links to the typeset PDF report for a session. The PDFs are pre-rendered by
// deep/make_pdf.py and staged into public/reports by scripts/copy-assets.mjs,
// so on the static site this is a plain download link — no server round-trip.

export function DownloadReportButton({
  sessionId,
  filename,
}: {
  sessionId: string;
  filename?: string;
}) {
  return (
    <a
      href={`/reports/${encodeURIComponent(sessionId)}.pdf`}
      download={`${filename ?? sessionId}.pdf`}
      className="flex shrink-0 items-center gap-2 rounded-sm border border-line2 px-4 py-2.5 font-mono text-[0.64rem] uppercase tracking-widest2 text-gold transition-colors hover:bg-gold/10"
    >
      <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M12 3v12m0 0 4-4m-4 4-4-4" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" strokeLinecap="round" />
      </svg>
      Download PDF
    </a>
  );
}
