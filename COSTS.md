# Cost and Performance Measurements

Measurements extracted from runs.jsonl.

| Stage | Calls | Success | Failed | Other | Latency (s) | GPU minutes | Known cost ($) | Unknown cost calls |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| keyframes | 20 | 20 | 0 | 0 | 163.598 | Unknown | 0.0000 | 20 |
| narration | 13 | 11 | 0 | 2 | 1092.615 | Unknown | 0.0000 | 13 |
| references | 10 | 10 | 0 | 0 | 78.014 | Unknown | 0.0000 | 10 |
| shots | 6 | 6 | 0 | 0 | 983.035 | 16.384 | 0.0000 | 6 |

## Infrastructure

- Gemini API for narration.
- Cloudflare Workers AI for images.
- Kaggle Tesla T4 GPUs for Wan and ACE-Step.
- Local CPU processing for FFmpeg assembly.

## Measurement limitations

- GPU minutes are elapsed inference measurements, not hardware utilization.
- Hosted API GPU usage is not directly observable.
- Missing billing values are unknown, not verified zero.
- Model downloads and initialization may not be included.
- SDK-internal retries may not appear as individual calls.
- Frontier-model comparisons were not performed.

## List-price equivalent

Pending verification against provider pricing.
