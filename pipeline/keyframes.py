
import argparse

from pipeline.core.config import settings
from pipeline.core.cache import cache
from pipeline.core.logger import logger
from pipeline.core.validator import (
    load_storyboard,
    validate_reference_files,
    resolve_reference_path,
)
from pipeline.providers.cloudflare import (
    CloudflareProvider,
)


STAGE = "keyframes"

OUTPUT_DIR = settings.outputs_dir / "keyframes"


def build_prompt(
    storyboard: dict,
    shot: dict,
) -> str:

    visual_style = storyboard["visual_style"]

    characters = {
        character["id"]: character
        for character in storyboard["characters"]
    }

    sections = [
        shot["image_prompt"],
        f"Visual style: {visual_style['description']}.",
        f"Composition: {visual_style['composition']}.",
    ]

    for index, character_id in enumerate(
        shot["character_ids"]
    ):
        character = characters[character_id]

        sections.append(
            f"Image {index} is the identity reference "
            f"for the following character: "
            f"{character['description']}. "
            "Preserve the character's recognizable "
            "facial features and appropriate age."
        )

    if shot["character_ids"]:
        sections.append(
            "Use reference images for character identity, "
            "not their portrait backgrounds or camera poses. "
            "Integrate the characters naturally into the "
            "requested cinematic scene."
        )

    sections.append(
        "Natural body proportions, realistic hands, "
        "coherent lighting, believable agricultural "
        "and environmental details. "
        "Single cinematic film frame."
    )

    return "\n".join(sections)


def get_dependencies(
    storyboard: dict,
    shot: dict,
) -> dict:

    characters = {
        character["id"]: character
        for character in storyboard["characters"]
    }

    return {
        character_id: resolve_reference_path(
            characters[character_id]["reference_image"]
        )
        for character_id in shot["character_ids"]
    }


def run(
    storyboard: dict,
    shot_id: str | None = None,
    force: bool = False,
) -> list:

    OUTPUT_DIR.mkdir(
        parents=True, exist_ok=True
    )

    shots = [
        shot
        for shot in storyboard["shots"]
        if shot_id is None or shot["id"] == shot_id
    ]

    if not shots:
        raise ValueError(
            f"Unknown shot ID: {shot_id}"
        )

    validate_reference_files(
        storyboard,
        shot_id=shot_id,
    )

    provider = None
    outputs = []

    width = storyboard["visual_style"]["width"]
    height = storyboard["visual_style"]["height"]

    for shot in shots:
        current_id = shot["id"]

        output_path = (
            OUTPUT_DIR / f"{current_id}.png"
        )

        prompt = build_prompt(
            storyboard, shot
        )

        dependencies = get_dependencies(
            storyboard, shot
        )

        parameters = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "seed": shot["seed"],
            "reference_order": shot["character_ids"],
            "provider_version": CloudflareProvider.VERSION,
        }

        key = cache.key(
            stage=STAGE,
            model=settings.image_model,
            parameters=parameters,
            dependencies=dependencies,
        )

        cached = (
            not force
            and cache.is_valid(
                stage=STAGE,
                artifact_id=current_id,
                key=key,
                output_path=output_path,
            )
        )

        if cached:
            print(f"[CACHE HIT] {current_id}")

            logger.cache_hit(
                stage=STAGE,
                artifact_id=current_id,
                cache_key=key,
                output_path=output_path,
            )

        else:
            print(f"[GENERATING] {current_id}")

            print(
                f"  References: "
                f"{shot['character_ids']}"
            )

            if provider is None:
                provider = CloudflareProvider()

            provider.generate_image(
                prompt=prompt,
                width=width,
                height=height,
                seed=shot["seed"],
                references=list(
                    dependencies.values()
                ),
                output_path=output_path,
                stage=STAGE,
                artifact_id=current_id,
            )

            cache.save(
                stage=STAGE,
                artifact_id=current_id,
                key=key,
                output_path=output_path,
            )

        outputs.append(output_path)

        print(f"  Output: {output_path}")

    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate storyboard keyframes"
    )

    parser.add_argument(
        "--storyboard",
        default=str(settings.storyboard_path),
    )

    parser.add_argument("--shot")

    parser.add_argument(
        "--force",
        action="store_true",
    )

    args = parser.parse_args()

    storyboard = load_storyboard(args.storyboard)

    run(
        storyboard,
        shot_id=args.shot,
        force=args.force,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
