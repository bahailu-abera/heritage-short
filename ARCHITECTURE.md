# Architecture

## Overview

The application is a modular Python pipeline for generating short narrated films from a structured storyboard.

```text
storyboard.json
       |
       v
Schema validation
       |
       +--------------------+
       |                    |
Character references    Narration
       |                    |
       v                    |
    Keyframes               |
       |                    |
       v                    |
 Moving shots          Selected music
       |                    |
       +---------+----------+
                 |
                 v
           FFmpeg assembly
                 |
        +--------+--------+
        |                 |
      16:9               9:16
```

## Stage contracts

| Stage | Inputs | Outputs |
|---|---|---|
| References | Character descriptions, seeds and visual style | Character PNGs |
| Narration | Narration text and voice settings | Per-shot WAV files |
| Keyframes | Image prompts, style and references | Per-shot PNG files |
| Shots | Keyframes, motion parameters and optional Wan clips | Duration-normalized MP4 clips |
| Music | Music direction and approved candidate | Selected soundtrack |
| Assembly | Video clips, narration, soundtrack and subtitles | Final MP4 exports |

## Validation

The storyboard is validated using JSON Schema and additional business rules. These include unique identifiers, valid character references, supported aspect ratios, shot timing constraints and total film duration.

## Content-based caching

Each cache key is derived from the generation stage, model identifier, parameters and content hashes of input dependencies.

An artifact is reused only when its cache key and output hash match the recorded manifest.

Changing a shot prompt invalidates the corresponding keyframe and video artifact. The final assembly is invalidated because one of its inputs has changed.

## Provider abstraction

External model integrations are separated from stage orchestration.

Gemini handles speech generation, Cloudflare handles image generation, and Kaggle runs Wan and ACE-Step.

The Wan provider validates imported clips using their manifests, seeds, prompts and keyframe hashes before allowing reuse.

## Failure handling

Network-dependent generation uses bounded retries for transient errors.

Artifacts are written to temporary files before replacing approved outputs. Invalid or stale Wan artifacts are rejected.

FFmpeg animation provides a deterministic alternative to GPU-intensive video generation.

## Observability

Model calls are recorded in runs.jsonl. Records capture available model identifiers, parameters, seeds, latency, GPU measurements, status and errors.

Unknown costs remain null rather than being represented as verified zero-cost inference.

## Final assembly

Each video shot is normalized to its storyboard duration. Narration is padded to the corresponding shot duration. The soundtrack is attenuated using sidechain compression while narration is present.

English subtitles and the AI disclosure end card are rendered during export.

## Limitations

Remote GPU jobs and soundtrack selection require manual intervention. The local pipeline consumes their approved artifacts.

The portrait export adapts horizontal compositions using a blurred background rather than generating native vertical keyframes.

The cache is designed for sequential execution. Distributed execution and concurrent cache writes are not currently supported.
