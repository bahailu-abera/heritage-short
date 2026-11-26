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
