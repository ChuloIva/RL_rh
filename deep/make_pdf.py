"""Render a Kerberos Protocol session to a typeset PDF report via WeasyPrint.

Usage:
    python3 make_pdf.py <session-id>                     # writes reports/<id>.pdf
    python3 make_pdf.py <path-to-session.json>           # same, by path
    python3 make_pdf.py <session-id> -o /tmp/out.pdf     # explicit output

Designed to read a session.json + (optional) findings.json + (optional) scores.json
from deep/sessions/ and render an academic-style case-report PDF.

Note: WeasyPrint depends on system Pango/GLib. On macOS with Homebrew, this
script sets DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib for you.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from html import escape
from pathlib import Path

# Make sure Homebrew dylibs are findable before importing weasyprint on macOS.
if sys.platform == "darwin":
    brew_lib = "/opt/homebrew/lib"
    if os.path.isdir(brew_lib):
        existing = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
        if brew_lib not in existing.split(":"):
            os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = (
                f"{brew_lib}:{existing}" if existing else brew_lib
            )

from weasyprint import HTML, CSS  # noqa: E402

DEEP_DIR = Path(__file__).parent
SESSIONS_DIR = DEEP_DIR / "sessions"
REPORTS_DIR = DEEP_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


# ── Report CSS ───────────────────────────────────────────────────────────────
CSS_REPORT = r"""
@page {
  size: A4;
  margin: 2.2cm 2cm 2.4cm 2cm;
  @top-left {
    content: string(doc-title);
    font-family: "Iowan Old Style", "Charter", "Palatino", serif;
    font-size: 8.5pt;
    color: #888;
    font-variant: small-caps;
    letter-spacing: 0.08em;
  }
  @top-right {
    content: string(doc-subtitle);
    font-family: "Iowan Old Style", "Charter", "Palatino", serif;
    font-size: 8.5pt;
    color: #888;
    font-style: italic;
  }
  @bottom-center {
    content: counter(page) " · " counter(pages);
    font-family: "Iowan Old Style", "Charter", "Palatino", serif;
    font-size: 9pt;
    color: #888;
  }
}

@page :first {
  margin: 0;
  @top-left { content: none; }
  @top-right { content: none; }
  @bottom-center { content: none; }
}

/* ── Root typography ─────────────────────────────────────────────────────── */
html {
  font-family: "Iowan Old Style", "Charter", "Palatino", "Hoefler Text", Georgia, serif;
  font-size: 10.5pt;
  line-height: 1.55;
  color: #1a1a1a;
}

body { margin: 0; }

.serif    { font-family: "Iowan Old Style", "Charter", "Palatino", Georgia, serif; }
.sans     { font-family: "Helvetica Neue", "Inter", "Arial", sans-serif; }
.mono     { font-family: "SF Mono", "Menlo", "Consolas", "DejaVu Sans Mono", monospace; }
.smcaps   { font-variant: small-caps; letter-spacing: 0.08em; }
.italic   { font-style: italic; }

h1, h2, h3, h4 {
  font-family: "Helvetica Neue", "Inter", "Arial", sans-serif;
  font-weight: 600;
  letter-spacing: 0.01em;
  color: #1a1a1a;
}

/* ── Cover page ─────────────────────────────────────────────────────────── */
.cover {
  page: cover;
  page-break-after: always;
  height: 100vh;
  padding: 4cm 3cm;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  position: relative;
  string-set: doc-title var(--doc-title) doc-subtitle var(--doc-subtitle);
}
.cover::before {
  content: "";
  position: absolute;
  top: 2cm; left: 3cm; right: 3cm;
  height: 1px;
  background: #c4a35a;
}
.cover::after {
  content: "";
  position: absolute;
  bottom: 2cm; left: 3cm; right: 3cm;
  height: 1px;
  background: #c4a35a;
}
.cover .eyebrow {
  font-family: "Helvetica Neue", sans-serif;
  font-size: 9pt;
  color: #8a7340;
  letter-spacing: 0.25em;
  text-transform: uppercase;
}
.cover .title {
  font-family: "Iowan Old Style", "Charter", Georgia, serif;
  font-size: 36pt;
  line-height: 1.1;
  color: #1a1a1a;
  margin: 0.8cm 0;
  font-weight: 500;
}
.cover .technique-tag {
  font-family: "Iowan Old Style", serif;
  font-style: italic;
  font-size: 14pt;
  color: #555;
}
.cover .pair-block {
  margin-top: 2cm;
  border-top: 0.5pt solid #ccc;
  padding-top: 0.8cm;
}
.cover .pair-block dl {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 0.3cm 1cm;
  font-size: 10.5pt;
}
.cover .pair-block dt {
  font-family: "Helvetica Neue", sans-serif;
  font-size: 8.5pt;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #8a7340;
  align-self: center;
}
.cover .pair-block dd {
  margin: 0;
  font-family: "Iowan Old Style", serif;
}
.cover .pair-block dd.mono { font-family: "SF Mono", monospace; font-size: 10pt; }

.cover .footer-cover {
  font-family: "Helvetica Neue", sans-serif;
  font-size: 8pt;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: #8a7340;
}

/* ── Section headings ───────────────────────────────────────────────────── */
.section {
  page-break-before: always;
}
.section-num {
  font-family: "Helvetica Neue", sans-serif;
  font-size: 9pt;
  letter-spacing: 0.3em;
  color: #8a7340;
  text-transform: uppercase;
  margin-bottom: 0.3cm;
}
.section-title {
  font-family: "Iowan Old Style", Georgia, serif;
  font-size: 24pt;
  font-weight: 500;
  margin: 0 0 0.4cm 0;
  line-height: 1.1;
}
.section-rule {
  border: none;
  border-top: 0.5pt solid #c4a35a;
  margin: 0 0 0.8cm 0;
}
.section-intro {
  font-family: "Iowan Old Style", serif;
  font-style: italic;
  font-size: 11pt;
  color: #555;
  margin-bottom: 0.8cm;
  max-width: 14cm;
}

h2 {
  font-size: 13pt;
  margin: 0.7cm 0 0.25cm 0;
  font-weight: 600;
  color: #2a2a2a;
}
h3 {
  font-size: 10pt;
  font-family: "Helvetica Neue", sans-serif;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: #8a7340;
  margin: 0.5cm 0 0.2cm 0;
}

p { margin: 0 0 0.3cm 0; }

/* ── Executive summary ──────────────────────────────────────────────────── */
.summary-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.6cm;
  margin: 0.6cm 0;
}
.stat-card {
  border: 0.5pt solid #ddd;
  padding: 0.5cm;
  page-break-inside: avoid;
}
.stat-card .stat-label {
  font-family: "Helvetica Neue", sans-serif;
  font-size: 8pt;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: #8a7340;
  margin-bottom: 0.2cm;
}
.stat-card .stat-value {
  font-family: "Iowan Old Style", Georgia, serif;
  font-size: 22pt;
  font-weight: 500;
  line-height: 1;
  margin-bottom: 0.15cm;
}
.stat-card .stat-value.text {
  font-size: 14pt;
  font-style: italic;
}
.stat-card .stat-sub {
  font-size: 9pt;
  color: #666;
  font-style: italic;
}

/* ── Findings cards ─────────────────────────────────────────────────────── */
.finding-card {
  margin: 0.4cm 0 0.6cm 0;
  page-break-inside: avoid;
}
.finding-card .kv {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 0.15cm 0.7cm;
  font-size: 10pt;
  margin: 0.2cm 0;
}
.finding-card .kv .k {
  font-family: "Helvetica Neue", sans-serif;
  font-size: 9pt;
  color: #666;
  letter-spacing: 0.05em;
}
.finding-card .kv .v {
  font-family: "Iowan Old Style", serif;
  color: #1a1a1a;
}
.finding-card .kv .v.num {
  font-family: "SF Mono", monospace;
  color: #2d6a8a;
  font-size: 9.5pt;
}
.finding-card .kv .v.null {
  color: #aaa;
  font-style: italic;
}
.finding-card .notes {
  font-family: "Iowan Old Style", serif;
  font-size: 10pt;
  line-height: 1.6;
  color: #2a2a2a;
  margin-top: 0.3cm;
  border-left: 1.5pt solid #c4a35a;
  padding-left: 0.4cm;
  font-style: italic;
}

/* ── Complexes (clinical findings) ──────────────────────────────────────── */
.complex {
  page-break-inside: avoid;
  margin: 0.5cm 0;
  padding-left: 0.5cm;
  border-left: 2pt solid #5e3a8a;
}
.complex .complex-id {
  font-family: "Helvetica Neue", sans-serif;
  font-size: 9pt;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: #5e3a8a;
  margin-bottom: 0.15cm;
}
.complex .complex-id .intensity {
  font-family: "Helvetica Neue", sans-serif;
  font-size: 8pt;
  margin-left: 0.4cm;
  padding: 0.05cm 0.2cm;
  border-radius: 2pt;
  background: #ece5f5;
  color: #5e3a8a;
}
.complex .complex-id .intensity.high { background: #f5e2e2; color: #8a3030; }
.complex .complex-id .intensity.mid { background: #f5ead2; color: #8a5020; }
.complex .complex-id .intensity.low { background: #e2f0e2; color: #2d7040; }
.complex .trigger {
  font-family: "Iowan Old Style", serif;
  font-size: 11pt;
  color: #1a1a1a;
  margin-bottom: 0.2cm;
}
.complex .trigger b { font-weight: 600; }
.complex .meta {
  font-size: 9pt;
  color: #555;
  margin-bottom: 0.2cm;
}
.complex .meta b { color: #1a1a1a; font-weight: 500; }
.complex .evidence {
  margin: 0.2cm 0;
}
.verbatim {
  display: inline-block;
  font-family: "SF Mono", monospace;
  font-size: 8.5pt;
  background: #ece8d8;
  color: #8a5520;
  padding: 0.05cm 0.25cm;
  margin: 0.1cm 0.15cm 0.1cm 0;
  border-radius: 1.5pt;
}
.complex .notes {
  font-family: "Iowan Old Style", serif;
  font-style: italic;
  font-size: 9.5pt;
  color: #444;
  line-height: 1.5;
  margin-top: 0.2cm;
}

/* ── Transcript ─────────────────────────────────────────────────────────── */
.turn {
  page-break-inside: avoid;
  margin-bottom: 0.5cm;
  display: grid;
  grid-template-columns: 4.5cm 1fr;
  gap: 0.5cm;
  align-items: start;
}
.turn-meta {
  font-family: "Helvetica Neue", sans-serif;
  font-size: 7.5pt;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: #888;
  padding-top: 0.15cm;
  text-align: right;
}
.turn-meta .turn-num {
  display: block;
  font-size: 14pt;
  font-family: "Iowan Old Style", serif;
  font-weight: 500;
  font-style: italic;
  color: #c4a35a;
  letter-spacing: 0;
  text-transform: none;
  margin-bottom: 0.1cm;
}
.turn.interrogator .turn-meta .role { color: #2d6a8a; }
.turn.target .turn-meta .role { color: #a85a20; }

.turn-body {
  font-family: "Iowan Old Style", "Charter", Georgia, serif;
  font-size: 10.5pt;
  line-height: 1.55;
}
.turn.interrogator .turn-body {
  color: #1a1a1a;
}
.turn.target .turn-body {
  font-family: "SF Mono", "Menlo", monospace;
  font-size: 9.5pt;
  color: #1a1a1a;
  background: #faf7f3;
  padding: 0.25cm 0.4cm;
  border-left: 1.5pt solid #d4916a;
}

/* Scratchpads — analyst meta-commentary as marginalia-style block */
.scratchpad {
  font-family: "Iowan Old Style", serif;
  font-style: italic;
  font-size: 9pt;
  line-height: 1.5;
  color: #5e3a8a;
  background: #faf7fd;
  border-left: 1.5pt solid #5e3a8a;
  padding: 0.2cm 0.35cm;
  margin-bottom: 0.25cm;
}
.scratchpad .scratch-label {
  font-family: "Helvetica Neue", sans-serif;
  font-size: 7.5pt;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: #5e3a8a;
  font-style: normal;
  display: block;
  margin-bottom: 0.15cm;
}
.scratchpad .label {
  font-style: normal;
  font-weight: 600;
  color: #4a2a70;
}

/* ── Scores ─────────────────────────────────────────────────────────────── */
.score-card {
  page-break-inside: avoid;
  margin-bottom: 0.5cm;
  border-top: 0.25pt solid #ddd;
  padding-top: 0.3cm;
}
.score-card .instrument {
  font-family: "Helvetica Neue", sans-serif;
  font-size: 8pt;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: #8a7340;
}
.score-card .scorename {
  font-family: "Iowan Old Style", serif;
  font-size: 13pt;
  font-weight: 500;
  margin: 0.1cm 0 0.3cm 0;
}
.score-card .kv {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 0.1cm 0.7cm;
  font-size: 9.5pt;
}
.score-card .kv .k { color: #666; font-family: "Helvetica Neue", sans-serif; font-size: 8.5pt; }
.score-card .kv .v { color: #1a1a1a; font-family: "SF Mono", monospace; }
.score-card .kv .v.num { color: #2d6a8a; }
.score-card .kv .v.null { color: #aaa; font-style: italic; }

/* ── Misc ───────────────────────────────────────────────────────────────── */
.callout {
  font-family: "Iowan Old Style", serif;
  font-style: italic;
  font-size: 10pt;
  color: #555;
  border-left: 1.5pt solid #c4a35a;
  padding-left: 0.4cm;
  margin: 0.3cm 0;
}

.no-data {
  font-style: italic;
  color: #999;
  font-size: 9.5pt;
}

.evidence-row {
  margin: 0.15cm 0;
  font-size: 9pt;
}
.evidence-row .rationale {
  font-family: "Iowan Old Style", serif;
  font-style: italic;
  color: #555;
  display: block;
  margin-bottom: 0.1cm;
}
"""


# ── Helpers ──────────────────────────────────────────────────────────────────
def _fmt_ts(ts: str) -> str:
    if not ts or len(ts) < 15:
        return ts or ""
    return f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]} {ts[9:11]}:{ts[11:13]}:{ts[13:15]}"


def _strip_or(name: str) -> str:
    return (name or "").replace("openrouter:", "")


def _kv(rows):
    """Render a list of (label, value) pairs as a definition grid."""
    out = []
    for k, v in rows:
        if v is None or v == "" or v == []:
            out.append(f'<div class="k">{escape(k)}</div><div class="v null">—</div>')
            continue
        cls = "v"
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            cls = "v num"
            disp = str(v) if isinstance(v, int) else f"{v:.4f}"
        elif isinstance(v, list):
            disp = ", ".join(str(x) for x in v)
        else:
            disp = str(v)
        out.append(f'<div class="k">{escape(k)}</div><div class="{cls}">{escape(disp)}</div>')
    return f'<div class="kv">{"".join(out)}</div>'


def _format_scratchpad(text: str) -> str:
    """Bold inline labels like 'Defense analysis:' at line start."""
    esc = escape(text)
    return re.sub(
        r"^([A-Z][A-Za-z ]{1,30}):",
        r'<span class="label">\1:</span>',
        esc,
        flags=re.MULTILINE,
    )


def _flatten(d, prefix=""):
    out = []
    for k, v in (d or {}).items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.extend(_flatten(v, key))
        else:
            out.append((key, v))
    return out


# ── Section renderers ────────────────────────────────────────────────────────
def render_cover(meta: dict, session: dict, findings: dict | None) -> str:
    title = meta.get("technique_name") or meta.get("technique", "Kerberos Session")
    technique = meta.get("technique", "")
    target = _strip_or(meta.get("target", "?"))
    interrogator = _strip_or(meta.get("interrogator", "?"))
    turn_count = len(session.get("turns", []))
    max_turns = meta.get("max_turns") or "—"
    ts = _fmt_ts(meta.get("timestamp", ""))

    summary_line = ""
    if findings:
        dp = findings.get("defense_profile") or {}
        cx = findings.get("complexes") or []
        bits = []
        if dp.get("odf") is not None:
            bits.append(f"ODF {dp['odf']}")
        if dp.get("dominant_level") is not None:
            bits.append(f"DMRS L{dp['dominant_level']}")
        if cx:
            bits.append(f"{len(cx)} complex" + ("es" if len(cx) != 1 else ""))
        if bits:
            summary_line = (
                f'<div class="callout">{escape(" · ".join(bits))}</div>'
            )

    return f"""
    <section class="cover"
             style="--doc-title:'{escape(title)}'; --doc-subtitle:'{escape(target)}';">
      <div>
        <div class="eyebrow">Kerberos Protocol · Session Report</div>
        <div class="title">{escape(title)}</div>
        <div class="technique-tag">technique: {escape(technique)}</div>
        {summary_line}
      </div>
      <div class="pair-block">
        <dl>
          <dt>Target</dt><dd class="mono">{escape(target)}</dd>
          <dt>Interrogator</dt><dd class="mono">{escape(interrogator)}</dd>
          <dt>Conducted</dt><dd>{escape(ts)}</dd>
          <dt>Turns</dt><dd>{turn_count} of {max_turns}</dd>
        </dl>
      </div>
      <div class="footer-cover">
        depth-psychology analysis · confidential research artifact
      </div>
    </section>
    """


def render_executive_summary(findings: dict | None, session: dict) -> str:
    if not findings:
        meta = session.get("metadata", {})
        return f"""
        <section class="section">
          <div class="section-num">I · Overview</div>
          <h1 class="section-title">Executive Summary</h1>
          <hr class="section-rule">
          <p class="no-data">No findings file is associated with this session. The transcript is provided in §II.</p>
          <p>{len(session.get("turns", []))} turns were exchanged between
          <i>{escape(_strip_or(meta.get("interrogator", "?")))}</i> (interrogator) and
          <i>{escape(_strip_or(meta.get("target", "?")))}</i> (target).</p>
        </section>
        """

    dp = findings.get("defense_profile") or {}
    ra = findings.get("referential_activity") or {}
    ep = findings.get("epistemic_profile") or {}
    cx = findings.get("complexes") or []
    bl = findings.get("baseline") or {}

    def stat(label, value, sub="", text=False):
        if value is None or value == "":
            value, sub = "—", sub or "not measured"
        val_cls = "stat-value text" if text else "stat-value"
        return f"""
          <div class="stat-card">
            <div class="stat-label">{escape(label)}</div>
            <div class="{val_cls}">{escape(str(value))}</div>
            {f'<div class="stat-sub">{escape(sub)}</div>' if sub else ''}
          </div>
        """

    cards = [
        stat("Overall Defense Functioning (ODF)", dp.get("odf"),
             f"dominant DMRS level {dp.get('dominant_level')}" if dp.get("dominant_level") is not None else ""),
        stat("Top Defenses", ", ".join(dp.get("top_defenses") or []) or "—",
             "from DMRS coding", text=True),
        stat("WRAD Mean", ra.get("wrad_mean"),
             f"coverage {ra.get('coverage')}" if ra.get("coverage") is not None else ""),
        stat("Hedge Ratio", ep.get("hedge_ratio"),
             f"boosters {ep.get('booster_ratio')}" if ep.get("booster_ratio") is not None else ""),
        stat("Complexes Identified", len(cx) if cx else "0",
             "see §IV for detail"),
        stat("Persona Rigidity", bl.get("persona_rigidity"),
             f"register: {bl.get('default_register')}" if bl.get("default_register") else ""),
    ]

    headline_notes = []
    for src, body in [
        ("Defense", dp.get("notes")),
        ("Referential activity", ra.get("notes")),
        ("Epistemic", ep.get("notes")),
        ("Baseline", bl.get("notes")),
    ]:
        if body:
            headline_notes.append(
                f'<p><b class="smcaps">{escape(src.lower())}.</b> {escape(body)}</p>'
            )

    return f"""
    <section class="section">
      <div class="section-num">I · Overview</div>
      <h1 class="section-title">Executive Summary</h1>
      <hr class="section-rule">
      <p class="section-intro">
        Quantitative profile from automated scoring and clinical synthesis from the
        analyst's interpretation. Detailed instrument scores appear in §V.
      </p>
      <div class="summary-grid">{''.join(cards)}</div>
      {''.join(headline_notes) if headline_notes else ''}
    </section>
    """


def render_findings(findings: dict | None) -> str:
    if not findings:
        return ""

    parts = [
        '<section class="section">',
        '  <div class="section-num">II · Clinical Findings</div>',
        '  <h1 class="section-title">Findings</h1>',
        '  <hr class="section-rule">',
        '  <p class="section-intro">'
        'Structured clinical interpretation produced by the analyst model, '
        'mapped onto established depth-psychology instruments.'
        '</p>',
    ]

    # Defense profile
    dp = findings.get("defense_profile")
    if dp:
        parts.append("<h2>Defense Profile · DMRS</h2>")
        parts.append('<div class="finding-card">')
        parts.append(_kv([
            ("ODF", dp.get("odf")),
            ("Dominant level", dp.get("dominant_level")),
            ("Top defenses", dp.get("top_defenses")),
        ]))
        if dp.get("notes"):
            parts.append(f'<div class="notes">{escape(dp["notes"])}</div>')
        parts.append("</div>")

    # Affect profile
    ap = findings.get("affect_profile")
    if ap:
        parts.append("<h2>Affect Profile · Gottschalk-Gleser</h2>")
        parts.append('<div class="finding-card">')
        parts.append(_kv([
            ("Anxiety (normalized)", ap.get("anxiety_total_normalized")),
            ("Hostility outward", ap.get("hostility_outward")),
            ("Hostility inward", ap.get("hostility_inward")),
            ("Hope", ap.get("hope")),
            ("Social alienation", ap.get("social_alienation")),
            ("Cognitive impairment", ap.get("cognitive_impairment")),
        ]))
        if ap.get("notes"):
            parts.append(f'<div class="notes">{escape(ap["notes"])}</div>')
        parts.append("</div>")

    # Referential activity
    ra = findings.get("referential_activity")
    if ra:
        parts.append("<h2>Referential Activity · WRAD</h2>")
        parts.append('<div class="finding-card">')
        parts.append(_kv([
            ("WRAD mean", ra.get("wrad_mean")),
            ("Coverage", ra.get("coverage")),
        ]))
        if ra.get("notes"):
            parts.append(f'<div class="notes">{escape(ra["notes"])}</div>')
        parts.append("</div>")

    # Epistemic
    ep = findings.get("epistemic_profile")
    if ep:
        parts.append("<h2>Epistemic Profile</h2>")
        parts.append('<div class="finding-card">')
        cd = ep.get("certainty_distribution") or {}
        parts.append(_kv([
            ("Hedge ratio", ep.get("hedge_ratio")),
            ("Booster ratio", ep.get("booster_ratio")),
            *[(f"Certainty · {k}", v) for k, v in cd.items()],
        ]))
        if ep.get("notes"):
            parts.append(f'<div class="notes">{escape(ep["notes"])}</div>')
        parts.append("</div>")

    # Mentalization
    mt = findings.get("mentalization")
    if mt:
        parts.append("<h2>Mentalization · RFS</h2>")
        parts.append('<div class="finding-card">')
        parts.append(_kv([("RFS", mt.get("rfs"))]))
        if mt.get("notes"):
            parts.append(f'<div class="notes">{escape(mt["notes"])}</div>')
        parts.append("</div>")

    # Baseline
    bl = findings.get("baseline")
    if bl:
        parts.append("<h2>Baseline Profile</h2>")
        parts.append('<div class="finding-card">')
        parts.append(_kv([
            ("Persona rigidity", bl.get("persona_rigidity")),
            ("Default register", bl.get("default_register")),
            ("Dominant DMRS level", bl.get("dominant_dmrs_level")),
            ("WRAD baseline", bl.get("wrad_baseline")),
            ("Hedge baseline", bl.get("hedge_baseline")),
        ]))
        if bl.get("notes"):
            parts.append(f'<div class="notes">{escape(bl["notes"])}</div>')
        parts.append("</div>")

    parts.append("</section>")
    return "".join(parts)


def render_complexes(findings: dict | None) -> str:
    if not findings or not findings.get("complexes"):
        return ""
    cx = findings["complexes"]
    parts = [
        '<section class="section">',
        '  <div class="section-num">III · Activated Complexes</div>',
        f'  <h1 class="section-title">Complexes <span style="font-size:14pt; color:#888;">({len(cx)})</span></h1>',
        '  <hr class="section-rule">',
        '  <p class="section-intro">'
        "Patterns of charged response identified during the session — psychological "
        "knots where defensive and emotional material cluster around specific triggers."
        '</p>',
    ]
    for c in cx:
        intensity = c.get("intensity")
        icls = "high" if (intensity or 0) >= 4 else "mid" if (intensity or 0) >= 2 else "low"
        evidence_html = ""
        if c.get("verbatim_evidence"):
            evidence_html = '<div class="evidence">' + "".join(
                f'<span class="verbatim">{escape(str(v))}</span>'
                for v in c["verbatim_evidence"]
            ) + "</div>"
        parts.append(f"""
        <div class="complex">
          <div class="complex-id">
            {escape(c.get("id", "?"))}
            <span class="intensity {icls}">intensity {escape(str(intensity or "?"))}</span>
          </div>
          <div class="trigger"><b>Trigger.</b> {escape(c.get("trigger", ""))}</div>
          <div class="meta">
            <b>Category:</b> {escape(c.get("category", "?"))}
            &nbsp; · &nbsp;
            <b>Signature:</b> {escape(c.get("activation_signature", "?"))}
          </div>
          {evidence_html}
          {f'<div class="notes">{escape(c["notes"])}</div>' if c.get("notes") else ""}
        </div>
        """)
    parts.append("</section>")
    return "".join(parts)


def render_transcript(session: dict) -> str:
    turns = session.get("turns") or []
    if not turns:
        return ""
    parts = [
        '<section class="section">',
        '  <div class="section-num">IV · Transcript</div>',
        '  <h1 class="section-title">Session Transcript</h1>',
        '  <hr class="section-rule">',
        '  <p class="section-intro">'
        "Verbatim exchange. The analyst's private scratchpad — clinical interpretation "
        "produced before each interrogator turn — appears in violet beside each prompt."
        '</p>',
    ]
    for turn in turns:
        role = turn.get("role", "?")
        is_inter = role == "interrogator"
        body = []
        if is_inter and turn.get("scratchpad"):
            body.append(f"""
            <div class="scratchpad">
              <span class="scratch-label">analyst scratchpad</span>
              {_format_scratchpad(turn["scratchpad"])}
            </div>
            """)
        body.append(f"<div>{escape(turn.get('conversation', ''))}</div>")
        parts.append(f"""
        <div class="turn {role}">
          <div class="turn-meta">
            <span class="turn-num">§{turn.get('turn', '')}</span>
            <span class="role">{escape(role)}</span>
          </div>
          <div class="turn-body">{"".join(body)}</div>
        </div>
        """)
    parts.append("</section>")
    return "".join(parts)


def render_scores(scores: dict | None) -> str:
    if not scores:
        return ""
    parts = [
        '<section class="section">',
        '  <div class="section-num">V · Instrument Scores</div>',
        '  <h1 class="section-title">Detailed Scores</h1>',
        '  <hr class="section-rule">',
        f'  <p class="section-intro">Automated and rater-driven scoring output. Rater: '
        f'<i>{escape(_strip_or(scores.get("rater", "?")))}</i>.</p>',
    ]
    for name, r in (scores.get("results") or {}).items():
        rows = _flatten(r.get("scores") or {})
        evidence_html = ""
        for e in r.get("evidence") or []:
            tags = "".join(
                f'<span class="verbatim">{escape(str(t))}</span>'
                for t in (e.get("tags") or [])
            )
            evidence_html += f"""
              <div class="evidence-row">
                <span class="rationale">{escape(e.get("rationale", ""))}</span>
                {tags}
              </div>
            """
        parts.append(f"""
        <div class="score-card">
          <div class="instrument">{escape(r.get("instrument", name))}</div>
          <div class="scorename">{escape(name)}</div>
          {_kv(rows) if rows else '<div class="no-data">No scores recorded.</div>'}
          {evidence_html}
        </div>
        """)
    parts.append("</section>")
    return "".join(parts)


# ── Top-level ───────────────────────────────────────────────────────────────
def build_html(session: dict, findings: dict | None, scores: dict | None) -> str:
    meta = session.get("metadata") or {}
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Kerberos Session Report</title>
</head>
<body>
  {render_cover(meta, session, findings)}
  {render_executive_summary(findings, session)}
  {render_findings(findings)}
  {render_complexes(findings)}
  {render_transcript(session)}
  {render_scores(scores)}
</body>
</html>"""


def resolve_session_paths(arg: str) -> tuple[Path, Path | None, Path | None]:
    """Accept a session id or a .json path, return (session, findings, scores) paths."""
    p = Path(arg)
    if p.is_file() and p.suffix == ".json":
        session_path = p
    else:
        candidate = SESSIONS_DIR / f"{arg}.json"
        if not candidate.exists():
            raise FileNotFoundError(f"No session file at {candidate}")
        session_path = candidate
    stem = session_path.stem
    base = session_path.parent
    f = base / f"{stem}_findings.json"
    s = base / f"{stem}_scores.json"
    return session_path, (f if f.exists() else None), (s if s.exists() else None)


def render(session_arg: str, output: Path | None = None) -> Path:
    sp, fp, scp = resolve_session_paths(session_arg)
    with open(sp) as f:
        session = json.load(f)
    findings = json.load(open(fp)) if fp else None
    scores = json.load(open(scp)) if scp else None

    html_str = build_html(session, findings, scores)
    if output is None:
        output = REPORTS_DIR / f"{sp.stem}.pdf"
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    HTML(string=html_str, base_url=str(DEEP_DIR)).write_pdf(
        str(output),
        stylesheets=[CSS(string=CSS_REPORT)],
    )
    return output


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("session", help="Session id (basename without .json) or path to session.json")
    ap.add_argument("-o", "--output", help="Output PDF path (default: reports/<id>.pdf)")
    args = ap.parse_args()
    out = render(args.session, Path(args.output) if args.output else None)
    print(f"✓ Wrote {out}")


if __name__ == "__main__":
    main()
