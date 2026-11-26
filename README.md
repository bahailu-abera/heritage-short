# From Soil to Silicon

### ከአፈር ወደ ቴክኖሎጂ

An AI-assisted autobiographical short film about growing up in rural Ethiopia, working alongside my mother on farmland, pursuing education, and developing an ambition to improve agricultural work through artificial intelligence.

## Film

- Duration: 87 seconds
- Narration: Amharic
- Subtitles: English
- Landscape: 1920 × 1080
- Portrait: 1080 × 1920
- Frame rate: 24 FPS
- Scenes: 10 shots and an AI disclosure end card

## Technology stack

| Stage | Technology |
|---|---|
| Storyboard | JSON and JSON Schema |
| Character references | FLUX.2 Klein via Cloudflare Workers AI |
| Keyframes | FLUX.2 Klein |
| Narration | Gemini TTS |
| Experimental video generation | Wan 2.2 TI2V-5B |
| Original soundtrack | ACE-Step 1.5 |
| Final shot animation | FFmpeg |
| Assembly | FFmpeg and Python |
| Artifact caching | SHA-256 content hashes |
| Logging | JSONL |
| GPU inference | Kaggle Tesla T4 |

## Architecture

The storyboard is the central contract between every generation stage. It defines characters, visual style, narration, prompts, shot durations, music cues and export settings.

The pipeline validates the storyboard before execution. Each generation stage independently checks whether its inputs have changed before producing a new artifact.

## Getting started

Prerequisites:

- Python 3.12 or newer, compatible with the installed dependencies
- FFmpeg and FFprobe 7.x with libx264 and libass support
- Gemini API credentials
- Cloudflare Workers AI credentials
- An approved ACE-Step soundtrack

Install dependencies:

```bash
make setup
source .venv/bin/activate
cp .env.example .env
```

Populate the environment variables in `.env`.

Generate soundtrack candidates using the ACE-Step notebook and place the approved soundtrack at:

```text
outputs/music/selected.wav
```

Alternatively, reuse the approved soundtrack included with the project artifacts, if available.

## Run the pipeline

```bash
make film
```

Final videos are written to:

```text
outputs/final/landscape.mp4
outputs/final/portrait.mp4
```

The default pipeline uses FFmpeg to animate AI-generated keyframes. The Wan backend is retained as an experimental alternative.

## Run individual stages

```bash
make references
make narration
make keyframes
make shots
make music
make assemble
```

Generate a specific keyframe:

```bash
python -m pipeline.keyframes --shot shot_004
```

Run validation and tests:

```bash
make validate
make test
```

## Selective regeneration

The cache incorporates model parameters, prompts, seeds and dependency hashes. Modifying one shot's image prompt invalidates that shot's keyframe and dependent video artifact while preserving unrelated outputs.

## Remote GPU generation

Wan and ACE-Step were executed on Kaggle. Their notebook implementations, generated artifacts and inference logs are retained for inspection.

GPU provisioning and soundtrack candidate selection are manual approval steps, not automatically managed by the local pipeline.

## Creative decisions

Four Wan video clips were generated successfully. However, the original FLUX keyframes produced better visual consistency for this particular film. The final version therefore uses cinematic pan-and-zoom animations.

## Documentation

- DESIGN.md: audience, intent and design decisions
- ARCHITECTURE.md: pipeline stages and caching
- EXPERIMENTS.md: measured experiments and creative comparisons
- FAILURES.md: technical blockers and resolutions
- COSTS.md: latency, GPU usage and cost measurements
- ETHICS.md: consent, licensing and AI disclosure
- runs.jsonl: model calls and processing logs

## AI disclosure

This film uses AI-generated fictional character representations, synthetic narration, generated images and original AI-generated music. It is based on my personal experiences, rather than actual documentary footage.
