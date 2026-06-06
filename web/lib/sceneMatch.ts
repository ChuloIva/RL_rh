import type { SessionScene, Turn } from "@/lib/types";

// Scene quotes are pulled verbatim from the transcript (see deep/video/make_scenes.py),
// so we can map each generated still back to the turn it came from. We try an
// exact (normalized) substring match on a shrinking prefix of the quote, then fall
// back to token overlap for quotes that were lightly paraphrased. Returns the array
// INDEX of the matching turn (matches how the page renders turns), or null.

function norm(s: string): string {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9 ]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function matchTurnIndex(quote: string, normTurns: string[]): number | null {
  const q = norm(quote);
  if (!q) return null;
  const words = q.split(" ");

  // Shrinking-prefix substring match: longest leading phrase that exists in a turn.
  for (let n = words.length; n > 3; n--) {
    const sub = words.slice(0, n).join(" ");
    for (let i = 0; i < normTurns.length; i++) {
      if (normTurns[i].includes(sub)) return i;
    }
  }

  // Token-overlap fallback for paraphrased quotes.
  const qs = new Set(words);
  let best: number | null = null;
  let bestScore = 0.45; // require a reasonable overlap before linking
  for (let i = 0; i < normTurns.length; i++) {
    const ts = new Set(normTurns[i].split(" "));
    let hit = 0;
    for (const w of qs) if (ts.has(w)) hit++;
    const score = qs.size ? hit / qs.size : 0;
    if (score > bestScore) {
      bestScore = score;
      best = i;
    }
  }
  return best;
}

/** Returns scenes enriched with an `anchorId` pointing at the source turn, when found. */
export function linkScenesToTurns(
  scenes: SessionScene[],
  turns: Turn[],
): SessionScene[] {
  const normTurns = turns.map((t) => norm(t.conversation ?? ""));
  return scenes.map((s) => {
    const idx = matchTurnIndex(s.quote, normTurns);
    return idx == null ? s : { ...s, anchorId: `turn-${idx}` };
  });
}
