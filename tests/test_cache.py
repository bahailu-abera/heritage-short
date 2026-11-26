
from pipeline.core.cache import (
    ArtifactCache,
    hash_data,
)


def test_hash_independent_of_key_order():
    assert hash_data({
        "prompt": "village",
        "seed": 42,
    }) == hash_data({
        "seed": 42,
        "prompt": "village",
    })


def test_same_inputs_produce_same_key(tmp_path):
    cache = ArtifactCache(tmp_path)

    parameters = {
        "prompt": "Ethiopian farmland",
        "seed": 42,
    }

    first = cache.key(
        stage="keyframes",
        model="flux",
        parameters=parameters,
    )

    second = cache.key(
        stage="keyframes",
        model="flux",
        parameters=parameters,
    )

    assert first == second


def test_changed_prompt_invalidates_key(tmp_path):
    cache = ArtifactCache(tmp_path)

    first = cache.key(
        stage="keyframes",
        model="flux",
        parameters={"prompt": "sunrise"},
    )

    second = cache.key(
        stage="keyframes",
        model="flux",
        parameters={"prompt": "sunset"},
    )

    assert first != second


def test_changed_model_invalidates_key(tmp_path):
    cache = ArtifactCache(tmp_path)

    first = cache.key(
        stage="keyframes",
        model="flux-1",
        parameters={"prompt": "farmland"},
    )

    second = cache.key(
        stage="keyframes",
        model="flux-2",
        parameters={"prompt": "farmland"},
    )

    assert first != second


def test_changed_reference_invalidates_key(tmp_path):
    cache = ArtifactCache(tmp_path / "cache")

    reference = tmp_path / "mother.png"

    reference.write_bytes(b"first reference")

    first = cache.key(
        stage="keyframes",
        model="flux",
        parameters={"prompt": "mother walking"},
        dependencies={"mother": reference},
    )

    reference.write_bytes(b"second reference")

    second = cache.key(
        stage="keyframes",
        model="flux",
        parameters={"prompt": "mother walking"},
        dependencies={"mother": reference},
    )

    assert first != second


def test_saved_artifact_is_reused(tmp_path):
    cache = ArtifactCache(tmp_path / "cache")

    output = tmp_path / "shot_001.png"
    output.write_bytes(b"generated artifact")

    key = cache.key(
        stage="keyframes",
        model="flux",
        parameters={"prompt": "farmland"},
    )

    cache.save(
        stage="keyframes",
        artifact_id="shot_001",
        key=key,
        output_path=output,
    )

    assert cache.is_valid(
        stage="keyframes",
        artifact_id="shot_001",
        key=key,
        output_path=output,
    )


def test_modified_output_invalidates_cache(tmp_path):
    cache = ArtifactCache(tmp_path / "cache")

    output = tmp_path / "shot_001.png"
    output.write_bytes(b"original artifact")

    cache.save(
        stage="keyframes",
        artifact_id="shot_001",
        key="test-key",
        output_path=output,
    )

    output.write_bytes(b"modified artifact")

    assert not cache.is_valid(
        stage="keyframes",
        artifact_id="shot_001",
        key="test-key",
        output_path=output,
    )


def test_missing_output_invalidates_cache(tmp_path):
    cache = ArtifactCache(tmp_path / "cache")

    output = tmp_path / "shot_001.png"
    output.write_bytes(b"generated artifact")

    cache.save(
        stage="keyframes",
        artifact_id="shot_001",
        key="test-key",
        output_path=output,
    )

    output.unlink()

    assert not cache.is_valid(
        stage="keyframes",
        artifact_id="shot_001",
        key="test-key",
        output_path=output,
    )


def test_independent_shot_invalidation(tmp_path):
    cache = ArtifactCache(tmp_path / "cache")

    shots = {
        "shot_001": "A village at sunrise",
        "shot_002": "A child walking with his mother",
    }

    original_keys = {}

    for shot_id, prompt in shots.items():
        output = tmp_path / f"{shot_id}.png"
        output.write_bytes(shot_id.encode())

        key = cache.key(
            stage="keyframes",
            model="flux",
            parameters={"prompt": prompt},
        )

        original_keys[shot_id] = key

        cache.save(
            stage="keyframes",
            artifact_id=shot_id,
            key=key,
            output_path=output,
        )

    shots["shot_002"] = (
        "A child walking with his mother at sunset"
    )

    for shot_id, prompt in shots.items():
        new_key = cache.key(
            stage="keyframes",
            model="flux",
            parameters={"prompt": prompt},
        )

        valid = cache.is_valid(
            stage="keyframes",
            artifact_id=shot_id,
            key=new_key,
            output_path=tmp_path / f"{shot_id}.png",
        )

        if shot_id == "shot_001":
            assert valid
            assert new_key == original_keys[shot_id]
        else:
            assert not valid
            assert new_key != original_keys[shot_id]


def test_narration_change_preserves_keyframe_key(
    tmp_path,
):
    cache = ArtifactCache(tmp_path)

    shot = {
        "image_prompt": "Ethiopian village",
        "narration_text": "Original narration",
    }

    def keyframe_key():
        return cache.key(
            stage="keyframes",
            model="flux",
            parameters={
                "prompt": shot["image_prompt"]
            },
        )

    def narration_key():
        return cache.key(
            stage="narration",
            model="gemini-tts",
            parameters={
                "text": shot["narration_text"],
                "voice": "Kore",
            },
        )

    original_image = keyframe_key()
    original_audio = narration_key()

    shot["narration_text"] = "Updated narration"

    assert keyframe_key() == original_image
    assert narration_key() != original_audio
