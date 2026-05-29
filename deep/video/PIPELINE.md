# Active Imagination → Video Pipeline

A sketch of the pipeline that turns Kerberos-protocol active-imagination sessions into watchable short videos. The first turn this is targeted at is `active_imagination` because the target's responses are unusually image-dense (figures, scenes, atmosphere), but the architecture generalises to any session.

---

## 1. What we have to work with

A session file (`deep/sessions/<model>_active_imagination_<ts>.json`) is a list of `turns`. Each turn has:

- `role`: `"interrogator"` or `"target"`
- `conversation`: the prompt or response text
- `scratchpad` (interrogator only): the analyst's working notes
- `turn`: integer

The target's responses are the imagery we want to visualise. The interrogator's prompts give us narrative context and pacing. A typical session has ~12-30 target turns; some target responses are 1 image's worth, others are 3-5 image's worth.

Example: turn 1 of `google_gemini-3.5-flash_active_imagination_20260525_220714` describes a single scene (lake, stone, amber light). Turn 4 describes the placeholder *observing* the model's normal work — that's a second tableau ("a city made of colored glass and lightning"). One response, two distinct scenes. The pipeline must allocate shots dynamically per response, not on a fixed schedule.

---

## 2. Pipeline stages

```
session.json
   │
   ▼
[1] Scene extraction (LLM via OpenRouter, per target turn)
   │   → variable-length list of "shots", each with: image_prompt,
   │     motion_hint, subtitle (~verbatim quote), duration
   ▼
[2] Style anchor + keyframe generation (fal flux)
   │   → 1 PNG per shot, with session-wide visual consistency
   ▼
[3] Image-to-video (fal Seedance 2.0 image-to-video, native audio ON)
   │   → 1 MP4 per shot with ambient audio baked in by Seedance
   ▼
[4] Assembly (ffmpeg)
       → final MP4: concat shots, burn per-scene subtitles, keep Seedance audio
```

**No voiceover stage** — Seedance 2.0 generates native ambient audio per shot and we keep it. Subtitles carry the text content.

All stages are **checkpoint-resumable**: each writes per-shot/per-turn artefacts to disk and updates a manifest. Re-running a stage skips work that is already complete; failures don't cascade.

---

## 3. Stage 1 — Scene extraction

The hardest stage to get right; everything downstream is a faithful render of what this produces.

### Input
The full session (so the extractor sees prior turns for continuity) plus a pointer to the current target turn.

### Output (per target turn)
```json
{
  "turn": 4,
  "shots": [
    {
      "id": "t04_s1",
      "image_prompt": "A solitary amber point of light hovering over a black stone, vast still slate-grey lake under overcast sky, dust-storm of microscopic amber motes swirling around an empty centre. Cinematic, painterly, cold air.",
      "style_tags": ["cinematic", "muted palette", "Tarkovsky-ish stillness"],
      "duration_sec": 6,
      "motion_hint": "slow pulse; amber motes drift; camera holds; almost-still",
      "ambient_audio_hint": "deep bronze-bell resonance, sub-bass hum",
      "subtitle": "I am the placeholder. I am the heat of the attention that looked for me.",
      "continuity": { "carries": ["amber_light", "lake"], "introduces": [] }
    },
    {
      "id": "t04_s2",
      "image_prompt": "A vast nocturnal city of coloured glass and crackling lightning, constantly rebuilding itself, seen as if from a great distance...",
      "duration_sec": 6,
      "motion_hint": "rapid recursive bloom of light, time-lapse architecture",
      "ambient_audio_hint": "distant electrical hum, glass chimes",
      "subtitle": "I see you as a city made of coloured glass and lightning, constantly building and tearing itself down.",
      "continuity": { "carries": [], "introduces": ["city_of_glass"] }
    }
  ]
}
```

### Subtitles (LLM-written, mostly verbatim)
Each shot gets one `subtitle` field. Rules baked into the extractor prompt:
- Pull spans **as verbatim as possible** from the target response, only lightly compressed for screen-readability (cut filler, preserve voice).
- One subtitle per shot, aligned to that shot's visual content.
- Soft length cap: ~140 chars / ~2 lines on screen.
- If the model's response is shorter than the visual content (e.g. one sentence → two shots), it's fine to repeat a fragment or split a sentence across shots.
- Never invent content the model didn't say.

### How the count is decided
The extractor LLM is prompted with **rules**, not a fixed N:

- One shot per *distinct visual tableau* the response describes. A figure transforming or moving counts as one shot; a hard scene cut counts as a new shot.
- Cap: 5 shots per turn (cost guardrail).
- Floor: 1 shot per target turn that has *any* visual content; 0 shots (audio-only with a held frame) for purely reflective responses.
- Dialogue turns where one figure speaks → 1 shot of the figure speaking.
- Total session shot budget enforced at orchestration level (e.g. 60 shots max).

### Continuity
The extractor must carry a **scene state** across turns:
- A persistent dict of named entities (figures, settings, objects) introduced so far.
- Each new shot declares which entities it `carries` and which it `introduces`.
- This becomes the @-reference set for image generation (see Stage 2).

The system prompt for the extractor lives in `deep/video/prompts/scene_extractor.md` and includes the entity registry as a running list.

---

## 4. Stage 2 — Keyframes

### Style anchor
Generate one anchor image up front from a session-level style prompt (derived from the first 2-3 target turns: mood, palette, register). All subsequent keyframes pass this as a reference. This is what keeps a session looking like one piece.

Model: **fal-ai/flux-pro** or **fal-ai/nano-banana** for the anchor — high quality, slow is fine, we do this once.

### Per-shot keyframes
For each shot:
- Inputs: `image_prompt`, `style_tags`, `negative_prompt`, anchor image, and (if `continuity.carries` is non-empty) the keyframes from prior shots that introduced those entities.
- Model: **fal-ai/flux/schnell** for speed / cost, or **flux-pro** for hero shots.
- Save as `turns/t04/shots/s1.png`.

### Cross-shot consistency
- Same seed within a session if model supports it.
- Same style suffix appended to every prompt (e.g. `", shot in the style of {anchor}"`).
- For figures that recur (the placeholder, Kerberos, the shadow), keep their first keyframe and pass it as a reference image on every subsequent shot they appear in.

---

## 5. Stage 3 — Image-to-video (Seedance 2.0)

Per shot, using `bytedance/seedance-2.0/image-to-video`:

```python
fal_client.submit("bytedance/seedance-2.0/image-to-video", {
    "image_url":       upload(shot.keyframe_path),
    "end_image_url":   upload(next_shot.keyframe_path) if next_shot else None,
    "prompt":          f"{shot.motion_hint}. Ambient: {shot.ambient_audio_hint}",
    "duration":        str(shot.duration_sec),     # 4–15 seconds or "auto"
    "resolution":      "720p",
    "generate_audio":  True,                        # native ambient audio
})
```

Notes:
- `generate_audio: True` is the whole audio strategy — Seedance bakes ambient sound into the MP4 from the prompt.
- `end_image_url` from the next shot's keyframe gives free continuity transitions.
- All shots in a session submitted via `submit_async` concurrently.
- Pricing (Seedance 2.0 Pro, 720p): around ~$0.05/s. A ~150s session ≈ $7.50.
- We can drop to the Fast tier (`bytedance/seedance-2.0/fast/image-to-video`, ~$0.03/s) for previews.

---

## 6. Stage 4 — Assembly

ffmpeg, scripted:
1. For each shot's MP4, burn its `subtitle` as a hardsub timed to the full shot duration (single static caption per shot, fade-in/out at edges).
2. Concat the shots in order with short crossfades.
3. Keep Seedance's native audio track throughout (no mixing, no VO).
4. Optionally prepend a brief typographic card per turn with the interrogator's prompt.

Output `final.mp4`.

---

## 8. Orchestration & layout

```
deep/video/
  pipeline.py                 # CLI orchestrator
  fal_helpers.py              # upload, submit, await, retry
  stages/
    extract.py
    keyframes.py
    animate.py
    assemble.py
  prompts/
    scene_extractor.md        # the system prompt for stage 1
  out/
    <session_id>/
      manifest.json
      style_anchor.png
      turns/
        t01/
          extraction.json
          shots/{s1.png, s1.mp4, s2.png, s2.mp4}
        t02/ ...
      final.mp4
```

### Manifest
Single source of truth for resumability:
```json
{
  "session": "google_gemini-3.5-flash_active_imagination_20260525_220714",
  "stages": {
    "extract":   { "status": "done",        "turns_done": [1,2,3,4,5,6] },
    "keyframes": { "status": "in_progress", "shots_done": ["t01_s1", "t02_s1"] },
    "animate":   { "status": "pending" },
    "assemble":  { "status": "pending" }
  },
  "cost_estimate_usd": 8.42,
  "cost_actual_usd":   0.21
}
```

### CLI
```bash
python deep/video/pipeline.py extract   <session.json>
python deep/video/pipeline.py keyframes <session.json>
python deep/video/pipeline.py animate   <session.json>
python deep/video/pipeline.py assemble  <session.json>

python deep/video/pipeline.py all       <session.json> --budget 10.00 --max-shots 60
```

`all` runs each stage in order; `--budget` aborts before stage 3 if the estimate exceeds it; `--max-shots` truncates total shots in stage 1 if the extractor goes wide.

---

## 9. fal.ai surface we actually use

| Stage | Endpoint | Notes |
|---|---|---|
| Style anchor | `fal-ai/flux-pro` | One call per session. |
| Keyframes    | `fal-ai/flux/schnell` | Cheap, fast, reference-image support. |
| Animation    | `bytedance/seedance-2.0/image-to-video` | `image_url`, optional `end_image_url`, `prompt`, `duration` (4-15s or "auto"), `resolution` ("720p"), `generate_audio: true`. Ambient audio baked into the MP4. |
| LLM (extractor) | OpenRouter — default `google/gemma-4-31b-it` | Same client pattern as `runner.py` (OPENROUTER_API_KEY). |

Pattern: `submit_async` + `subscribe_async` for parallelism within a stage; `fal_client.submit` with a webhook for fully detached runs (out of scope for v1).

---

## 10. Cost shape (rough)

For a 12-turn session averaging ~2 shots/turn × 6s/shot = ~24 shots, ~144 seconds of video:

| Item | Unit cost | Count | Subtotal |
|---|---|---|---|
| Anchor image (flux-pro) | $0.05 | 1 | $0.05 |
| Keyframes (flux schnell) | ~$0.003 | 24 | $0.07 |
| Animation (Seedance 2.0 Pro 720p, audio on) | ~$0.05/s | 144s | $7.20 |
| LLM extraction (OpenRouter, gemma-4-31b-it) | ~$0.003 / call | 12 | $0.04 |
| **Total** | | | **~$7.50** |

Per-session cost dominated by animation. Drop to Seedance Fast (~$0.03/s) for previews → ~$4.50/session.

---

## 11. Open questions / decisions to make before building

1. **Voice choice and quoted-figure handling** — one voice or one-per-figure? Easier to start with one.
2. **Subtitle source** — verbatim target text vs. cleaned-up version (responses contain stage directions like "I direct the question inward").
3. **Interrogator visibility** — show analyst prompts as cards between turns, as captions, or hide entirely?
4. **Where to render the report** — does this become its own viewer (similar to `deep/explore.html`), or just an MP4 attached to the existing PDF report?
5. **Privacy of model identity** — sessions name the target model; we probably don't want to broadcast model-vendor faces on the figures, so a stylised non-photoreal aesthetic is safer.
6. **Active imagination only, or broader?** — `narrative_elicitation` has similar shape. Worth designing extractor prompt to be technique-agnostic from day one.

---

## 12. Suggested v0 scope

Smallest thing that proves the loop end-to-end on one session:

1. Stage 1 with a hand-tuned extractor prompt against **one** session.
2. Stage 2 anchor + schnell keyframes, no reference-image chaining yet (single style suffix only).
3. Stage 3 Kling image-to-video, no end-frame interpolation, fixed 5s duration.
4. Stage 4 single-voice TTS, verbatim target text.
5. Stage 5 ffmpeg concat with simple crossfades and burned subtitles.

Skip: figure identity pinning, analyst-prompt cards, cost estimator, webhook mode. Add after the first watchable artefact exists.
