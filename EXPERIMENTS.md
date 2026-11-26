## E002 — Artifact-level cache invalidation

### Hypothesis

Hashing only stage-specific inputs will prevent
unnecessary regeneration when an unrelated storyboard
property changes.

### Method

Created isolated tests with two independently cached
shots. Changed the image prompt of the second shot
and checked both cache entries.

Also tested whether changing narration affects the
keyframe cache key.

### Result

Pending execution.

### Decision

Use stage-specific dependency hashes instead of
hashing the entire storyboard for every artifact.
