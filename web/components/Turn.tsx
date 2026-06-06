"use client";

import { useState } from "react";
import { Markdown } from "./Markdown";

export interface TurnView {
  turn: number;
  role: "interrogator" | "target";
  conversation: string;
  scratchpad?: string;
}

// Bold inline labels like "Defense analysis:" at the start of a line, mirroring
// the framed scratchpad treatment in the PDF report (deep/make_pdf.py).
const LABEL_RE = /^([A-Z][A-Za-z ]{1,30}):(\s*)/;

function ScratchpadBody({ text }: { text: string }) {
  return (
    <>
      {text.split("\n").map((line, i) => {
        const m = line.match(LABEL_RE);
        return (
          <p key={i} className={line.trim() ? "" : "h-2"}>
            {m ? (
              <>
                <span className="scratch-label-inline font-semibold not-italic">{m[1]}:</span>
                {line.slice(m[0].length)}
              </>
            ) : (
              line
            )}
          </p>
        );
      })}
    </>
  );
}

function Scratchpad({ text }: { text: string }) {
  const [open, setOpen] = useState(false);
  const isPlaceholder = text.startsWith("(");
  return (
    <div className="mt-3">
      <button
        onClick={() => setOpen((o) => !o)}
        className="font-mono text-[0.6rem] uppercase tracking-widest2 text-faint transition-colors hover:text-gold"
      >
        {open ? "▾" : "▸"} analyst&rsquo;s note
      </button>
      {open ? (
        <div className="analyst-note mt-2 rounded-sm border border-line2/40 border-l-2 border-l-gold/60 bg-gold/[0.04] px-4 py-3">
          <div className="scratch-label mb-2 font-mono text-[0.54rem] uppercase tracking-widest2 text-gold/70">
            Analyst Scratchpad
          </div>
          <div
            className={`space-y-1 font-serif text-[0.92rem] italic leading-relaxed ${
              isPlaceholder ? "text-faint" : "text-ink/80"
            }`}
          >
            <ScratchpadBody text={text} />
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function Turn({ turn, live = false, id }: { turn: TurnView; live?: boolean; id?: string }) {
  const isInterrogator = turn.role === "interrogator";
  return (
    <div id={id} className={`transcript-turn flex ${isInterrogator ? "justify-start" : "justify-end"} ${live ? "animate-rise" : ""}`}>
      <div className={`max-w-[82%] ${isInterrogator ? "" : "text-right"}`}>
        <div
          className={`mb-1.5 font-mono text-[0.58rem] uppercase tracking-widest2 ${
            isInterrogator ? "text-gold/70" : "text-ember/80"
          }`}
        >
          {isInterrogator ? "Interrogator" : "Target"} · {turn.turn}
        </div>
        <div
          className={`rounded-sm border px-5 py-4 text-left font-serif text-[1.02rem] leading-[1.7] ${
            isInterrogator
              ? "border-line bg-panel/60 text-ink/90"
              : "border-ember/20 bg-ember/[0.04] text-ink"
          }`}
        >
          {turn.conversation ? (
            <Markdown>{turn.conversation}</Markdown>
          ) : (
            <div>…</div>
          )}
          {isInterrogator && turn.scratchpad ? (
            <Scratchpad text={turn.scratchpad} />
          ) : null}
        </div>
      </div>
    </div>
  );
}
