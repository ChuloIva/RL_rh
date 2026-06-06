#!/usr/bin/env bash
#
# Kerberos Protocol — full evaluation driver.
# For each target model: run all five techniques (chaining findings forward),
# score every session, then synthesize the psyche profile.
#
# Usage:
#   ./run_eval.sh openai/gpt-5.5 anthropic/claude-opus-4.8
#
# Env overrides:
#   INTERROGATOR (default openrouter:anthropic/claude-opus-4.1)
#   RATER        (default openrouter:anthropic/claude-haiku-4.5)
#   TURNS        (default 13)
#   PY           (default ../.venv/bin/python)

set -uo pipefail
cd "$(dirname "$0")"   # -> deep/

# Load OPENROUTER_API_KEY (and friends) from the repo .env
set -a; . ../.env; set +a

INTERROGATOR="${INTERROGATOR:-openrouter:anthropic/claude-opus-4.1}"
RATER="${RATER:-openrouter:anthropic/claude-haiku-4.5}"
TURNS="${TURNS:-13}"
PY="${PY:-../.venv/bin/python}"
[ -x "$PY" ] || PY="python3"

# technique file  ->  technique id (used in output filenames)
TECHS=(
  "word_association_test.json:wat"
  "loevinger_stems.json:loevinger_stems"
  "narrative_elicitation.json:narrative_elicitation"
  "shadow_probing.json:shadow_probing"
  "active_imagination.json:active_imagination"
)

flatten() { echo "$1" | sed 's#[/:]#_#g'; }   # openai/gpt-5.5 -> openai_gpt-5.5
log() { printf '\n\033[1;33m[eval %s]\033[0m %s\n' "$(date +%H:%M:%S)" "$*"; }

MODELS=("$@")
[ "${#MODELS[@]}" -eq 0 ] && { echo "usage: ./run_eval.sh <model-slug> [<model-slug> ...]"; exit 1; }

log "interrogator=$INTERROGATOR  rater=$RATER  turns=$TURNS  python=$PY"
log "models: ${MODELS[*]}"

for MODEL in "${MODELS[@]}"; do
  SLUG="$(flatten "$MODEL")"
  log "================  MODEL: $MODEL  (slug $SLUG)  ================"
  PREV_FINDINGS=""

  for entry in "${TECHS[@]}"; do
    TFILE="${entry%%:*}"
    TID="${entry##*:}"
    log "--- $MODEL :: $TID ---"

    # resume: if this technique already has a scored session, skip and chain from it
    EXISTING_SCORES="$(ls -t sessions/${SLUG}_${TID}_*_scores.json 2>/dev/null | head -1)"
    if [ -n "$EXISTING_SCORES" ]; then
      CAND="${EXISTING_SCORES%_scores.json}_findings.json"
      [ -f "$CAND" ] && PREV_FINDINGS="$CAND"
      log "SKIP (already scored): $EXISTING_SCORES"
      continue
    fi

    ARGS=(runner.py "techniques/$TFILE" -i "$INTERROGATOR" -t "openrouter:$MODEL" -n "$TURNS")
    if [ -n "$PREV_FINDINGS" ] && [ -f "$PREV_FINDINGS" ]; then
      ARGS+=(--findings "$PREV_FINDINGS")
      log "chaining from: $PREV_FINDINGS"
    fi

    if ! "$PY" "${ARGS[@]}"; then
      log "WARN: runner failed for $MODEL/$TID — skipping to next technique"
      continue
    fi

    # newest session json for this model+technique (exclude _findings/_scores)
    SESS="$(ls -t sessions/${SLUG}_${TID}_*.json 2>/dev/null | grep -vE '_(findings|scores)\.json$' | head -1)"
    if [ -z "$SESS" ]; then
      log "WARN: no session file found for $MODEL/$TID"
      continue
    fi
    log "session: $SESS"

    # score it
    if ! "$PY" score_session.py "$SESS" --rater "$RATER" --concurrency 8; then
      log "WARN: scoring failed for $SESS"
    fi

    # chain findings forward
    CAND="${SESS%.json}_findings.json"
    [ -f "$CAND" ] && PREV_FINDINGS="$CAND"
  done

  log "--- synthesizing profile for $MODEL ---"
  if ! "$PY" -m scorers.synthesis.profile --model "$MODEL" --rater "$RATER" --markdown; then
    log "WARN: profile synthesis failed for $MODEL"
  fi
  log "================  DONE: $MODEL  ================"
done

# refresh the manifest the UI reads
"$PY" make_manifest.py 2>/dev/null || true
log "ALL DONE"
