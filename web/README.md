# Kerberos Protocol — UI

A minimalistic / poetic / occult Next.js front-end for the `deep/` depth-psychology harness.

- **Home** — the protocol's premise + a card per analyzed model.
- **Model** — the synthesized profile (archetype scores, complex map, Kerberos topology, narrative) and that model's sessions.
- **Session** — the full interrogation transcript (with the analyst's scratchpad), extracted complexes, and instrument scores.
- **Descend (`/run`)** — paste an OpenRouter API key, pick a target + technique, and watch the interrogation stream live.

## Run

```bash
cd web
npm install
npm run dev
# http://localhost:3000
```

The app reads `../deep/sessions/` directly from disk at request time. Override the location with `DEEP_DIR=/abs/path/to/deep`.

## Live runs

`/run` POSTs to `/api/run`, which spawns `deep/runner.py` with `KERBEROS_STREAM=1` and your key as a request-scoped `OPENROUTER_API_KEY` (never persisted). It prefers the repo `venv/bin/python` if present, else `python3`. Scoring stays a separate offline step (`deep/score_session.py`).
