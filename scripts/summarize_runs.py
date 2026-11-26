import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

records = []

for line in (ROOT / "runs.jsonl").read_text().splitlines():
    if line.strip():
        records.append(json.loads(line))

stats = defaultdict(
    lambda: {
        "calls": 0,
        "success": 0,
        "failed": 0,
        "other": 0,
        "latency": 0.0,
        "gpu_minutes": 0.0,
        "gpu_measured": 0,
        "cost": 0.0,
        "unknown_cost": 0,
    }
)

for record in records:

    if record.get("event") != "model_call":
        continue

    stage = record.get("stage", "unknown")

    stat = stats[stage]

    stat["calls"] += 1

    status = record.get("status")

    if status == "success":
        stat["success"] += 1
    elif status == "failed":
        stat["failed"] += 1
    else:
        stat["other"] += 1

    stat["latency"] += (
        record.get("latency_seconds") or 0
    )

    gpu_minutes = record.get("gpu_minutes")

    if gpu_minutes is not None:
        stat["gpu_minutes"] += gpu_minutes
        stat["gpu_measured"] += 1

    cost = record.get("cost_usd")

    if cost is None:
        stat["unknown_cost"] += 1
    else:
        stat["cost"] += cost

lines = [
    "# Cost and Performance Measurements",
    "",
    "Measurements extracted from runs.jsonl.",
    "",
    "| Stage | Calls | Success | Failed | Other | Latency (s) | GPU minutes | Known cost ($) | Unknown cost calls |",
    "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
]

for stage, stat in sorted(stats.items()):

    gpu = (
        f"{stat['gpu_minutes']:.3f}"
        if stat["gpu_measured"]
        else "Unknown"
    )

    lines.append(
        f"| {stage} "
        f"| {stat['calls']} "
        f"| {stat['success']} "
        f"| {stat['failed']} "
        f"| {stat['other']} "
        f"| {stat['latency']:.3f} "
        f"| {gpu} "
        f"| {stat['cost']:.4f} "
        f"| {stat['unknown_cost']} |"
    )

lines += [
    "",
    "## Infrastructure",
    "",
    "- Gemini API for narration.",
    "- Cloudflare Workers AI for images.",
    "- Kaggle Tesla T4 GPUs for Wan and ACE-Step.",
    "- Local CPU processing for FFmpeg assembly.",
    "",
    "## Measurement limitations",
    "",
    "- GPU minutes are elapsed inference measurements, not hardware utilization.",
    "- Hosted API GPU usage is not directly observable.",
    "- Missing billing values are unknown, not verified zero.",
    "- Model downloads and initialization may not be included.",
    "- SDK-internal retries may not appear as individual calls.",
    "- Frontier-model comparisons were not performed.",
    "",
    "## List-price equivalent",
    "",
    "Pending verification against provider pricing.",
    "",
]

output = ROOT / "COSTS.md"

output.write_text(
    "\n".join(lines),
    encoding="utf-8",
)

print(output.read_text())
