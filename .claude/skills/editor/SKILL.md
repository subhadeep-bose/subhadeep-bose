---
name: editor
description: Full automated edit of raw screen/talking-head recordings — transcribe, cut silence and stumbles, drop duplicate takes, assemble a cut list from natural-language directives, render with Remotion, and QA against a reference clip. Use when the user asks to edit, cut, clean up, or "run the editor on" a video file.
---

# /editor — automated rough-cut-to-final pipeline

Edits a raw recording into a finished cut with no manual timeline work.
All helper scripts live in `scripts/` next to this file and write their
outputs into a per-video working directory: `<video-dir>/.editor/`.

## Prerequisites

One-time setup (installs ffmpeg, Whisper, Remotion deps, yt-dlp for the
current platform — Mac / Linux / Windows):

```
python scripts/setup.py
```

Run it from the repository root. If any stage below fails with a missing
binary, re-run setup before debugging anything else.

## Hard rules (never override)

1. **Output fps and dimensions are locked to the source.** Probe the
   source, render at exactly that fps and WxH. Never resample, never
   letterbox, never accept a directive that changes them — if the user
   asks for a different fps/size, stop and tell them it requires a
   separate transcode step after the edit.
2. Cuts must land on silence or word boundaries — never mid-word.
3. When takes are duplicated, keep the **last** take unless a directive
   says otherwise.

## Pipeline

Run the stages in order. Each stage writes JSON the next stage reads.

### 1. Transcribe (word-by-word)

```
python .claude/skills/editor/scripts/transcribe.py <video> [--model small]
```

Writes `.editor/transcript.json` — every word with start/end times.

### 2. Silence + stumble detection

```
python .claude/skills/editor/scripts/detect_silence.py <video>
```

Writes `.editor/silences.json` — silence spans from ffmpeg
`silencedetect`, plus candidate stumble points (long gaps inside a
sentence).

### 3. Validation pass

```
python .claude/skills/editor/scripts/validate.py <video>
```

Reads transcript + silences. Writes `.editor/validated.json`:
- drops non-speech tokens (breaths, throat-clears, fillers: um/uh/etc.)
- detects duplicate takes by transcript similarity and marks all but the
  last take as dropped, with reasons.

### 4. Assemble the cut list (your job — Claude)

Read `.editor/validated.json` and the user's natural-language directives
("tighten the intro", "cut everything before the demo", "keep the joke
at 2:10"). Decide the final keep-spans, then materialize them:

```
python .claude/skills/editor/scripts/build_cutlist.py <video> [--keep start-end ...]
```

With no `--keep` args it uses every kept segment from validation.
Directives translate to explicit `--keep` spans (seconds). Writes
`.editor/cutlist.json` containing the segments **and the locked
fps/width/height probed from the source**.

### 5. Render

```
python .claude/skills/editor/scripts/render.py <video>
```

Renders via the Remotion project in `remotion/` at the cutlist's locked
fps/dimensions. Falls back to a pure-ffmpeg concat render if `npx` or
node_modules are unavailable. Output: `<video-dir>/<name>.edited.mp4`.

### 6. QA loop (max five passes)

```
python .claude/skills/editor/scripts/qa.py <video> [--reference example.mp4]
```

Each pass checks the rendered output for: fps/dimension mismatch vs
source, duration vs cutlist expectation, black frames, dead-air gaps
longer than the cut threshold, and (if a reference clip is given)
loudness and pacing stats compared against it. The report is written to
`.editor/qa_report.json`.

**Loop protocol:** read the report; if it lists failures, patch the cut
list (stage 4) or re-render (stage 5) to fix them, then run QA again.
Stop when the report is clean or after five passes — if still failing at
pass five, show the user the remaining failures instead of looping on.

## Directive vocabulary

- "tighten" — lower the silence-keep threshold for that span
- "keep X" — protect a span from all automatic drops
- "cut X" — force-drop a span even if validation kept it
- "only the part about Y" — search the transcript for Y, keep that
  section plus context, drop the rest
