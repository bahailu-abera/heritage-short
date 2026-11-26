## F001 — Gemini TTS API incompatibility

### Problem
The speech generation request returned HTTP 400
INVALID_ARGUMENT because the endpoint rejected speechConfig.

### Investigation
Checked the updated Gemini TTS documentation and found
that Gemini 3.8 Flash TTS documents an Interactions API
workflow rather than our generateContent implementation.

### Attempted fix
Updated the Google GenAI SDK and migrated the TTS
request to client.interactions.create().

### Status
Pending verification.

### Lesson
Model availability alone does not guarantee API
compatibility. Verify the request and response contracts
before integrating a model into the pipeline.


### Second attempt

Migrating to the Interactions API resulted in a
404 model-not-found error.

### Investigation

Discovered that the SDK's default API version
may not expose the TTS model.

### Proposed fix

Explicitly configure the SDK to use v1beta.

### Status

worked

## F002 — Unsupported FLUX generation parameter

### Problem
Cloudflare Workers AI returned HTTP 400 with error
code 5006 because the seed parameter was unsupported.

### Root cause
Assumed that the hosted FLUX.1 schnell endpoint
accepted standard image generation parameters.

### Fix
Removed the seed parameter from the request payload.

### Status
worked

### Lesson
Each model integration needs its own input contract.
Model parameters cannot be assumed to be interchangeable.
Unsupported seeds must be logged as null.

## F004 — Gemini TTS rate limiting

### Problem

Narration generation appeared to stall on shot_009
and subsequently on shot_010.

### Root cause

The Gemini SDK received HTTP 429 Too Many Requests.
Its internal retry mechanism entered a backoff sleep,
making the pipeline appear unresponsive.

The exact quota threshold was not established.

### Resolution

Interrupted the stalled requests and retried the
affected shots individually.

Both shots were eventually generated successfully.

Previously generated narration files were preserved
through artifact-level caching.

### Lesson

Provider SDK retries can interact with application-level
retry mechanisms and obscure request progress.

Independent artifact caching makes partial pipeline
failures recoverable without repeating successful work.

### Status

Resolved for the current narration batch.

### Verified resolution

Installed FFmpeg 7.0.2-static and FFprobe inside
the project's .venv/bin directory.

Verified support for:
- amix normalization
- sidechaincompress
- loudnorm
- subtitles

Successfully rendered the 87-second radio cut.

The system FFmpeg installation remained unchanged.

### Status

Resolved.
