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


## Narrator voice selection

### Hypothesis
Algenib's gravelly vocal character will provide
a more immersive autobiographical narration than
the original Kore voice.

### Method
Generate the same Amharic narration using Algenib,
Charon and Orus while keeping the narration text,
model and style instructions unchanged.

### Result
Pending listening evaluation.

### Decision
Pending voice selection.

## E004 — Narration-driven shot timing

### Hypothesis

Allocating shot durations before measuring generated
speech may cause narration to exceed its planned slot.

### Method

Generated ten independent Amharic narration files
and measured their duration using FFprobe.

### Result

Four narration segments exceeded their allocated time:

- shot_003: 8.47s instead of 8s
- shot_005: 9.24s instead of 9s
- shot_008: 8.18s instead of 8s
- shot_010: 8.11s instead of 8s

Total measured narration duration was 76.75 seconds.

### Decision

Extended the four affected shots by one second each.

The planned film duration increased from 83 to 87
seconds, preserving natural speech pacing without
exceeding the assignment's duration limit.

## E009 — Independent adolescent generation

### Hypothesis

Conditioning the teenage portrait on the childhood
portrait causes excessive preservation of childhood
facial and physical characteristics.

### Change

Removed the child-to-teenager reference dependency,
strengthened the adolescent physical description,
and changed the generation seed.

### Result

The independently generated teenage portrait showed
better visible physical maturation and was approved
by the creator.

### Decision

Prioritize age accuracy over exact facial similarity
when generating different life stages.

### Trade-off

Independent generation may reduce facial identity
consistency across different ages.

Multiple generation parameters were changed together,
so the individual effect of each change was not isolated.

## E010 — Wan versus FFmpeg visual quality

### Hypothesis
Generative video motion would improve the cinematic
quality of the film compared with animated keyframes.

### Experiment
Generated four Wan video clips and compared them
against FFmpeg pan-and-zoom animations.

### Result
The creator preferred the visual quality of the
original keyframes over the Wan-generated footage.

### Decision
Use FFmpeg pan-and-zoom animations for all ten
shots in the final film.

### Trade-off
Reduced natural subject movement in exchange for
better visual consistency and preservation of
the original compositions.
