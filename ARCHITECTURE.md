# Architecture

## Pipeline contract

storyboard.json is the shared contract between all
generation and assembly stages.

JSON Schema validates structural constraints.
Python validation enforces film duration, unique IDs,
character dependencies and music cue relationships.

## Model integration

Provider-specific request construction is isolated
from pipeline stage logic.

Model names and API versions are configurable.

## Caching

Artifacts are cached independently by stage and
artifact ID.

Cache keys use SHA-256 hashes derived from:

- Model identifier
- Effective generation parameters
- Upstream artifact contents
- Cache implementation version

Output hashes are stored in cache manifests to detect
missing or modified artifacts.

Only successful, validated artifacts are cached.

Changing narration should not invalidate visual assets
when shot timing remains unchanged.

## Failure handling

Transient API failures use bounded exponential
backoff with jitter.

Invalid requests and authentication failures are
not automatically retried.

GPU memory and quota failures will be handled through
stage-specific recovery and alternative backends.

## Observability

Model attempts are logged individually in runs.jsonl.

Logs distinguish model calls, failures, scheduled
retries and cache hits.

Actual costs and estimated commercial costs are
recorded separately.

## Current limitations

The cache retains one current manifest per artifact.

Concurrent generation of the same artifact is
not supported.

Provider inference and end-to-end regeneration
still require integration testing.
