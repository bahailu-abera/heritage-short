
import argparse

from pipeline.core.config import settings
from pipeline.core.cache import cache
from pipeline.core.logger import logger
from pipeline.core.validator import (
    load_storyboard,
    resolve_reference_path,
)
from pipeline.providers.cloudflare import (
    CloudflareProvider,
)


STAGE = "references"

REFERENCE_WIDTH = 512
REFERENCE_HEIGHT = 512

AGE_DEPENDENCIES = {
    "adult_student": "boy_teenager",
}

def build_prompt(
    character: dict,
    visual_style: dict,
    parent_id: str | None,
) -> str:

    prompt = (
        "Create a realistic fictional character reference "
        "portrait for a cinematic autobiographical film. "
        f"{character['description']}. "
        "Centered waist-up portrait showing the face, "
        "neck, shoulders and upper body. "
        "Neutral facial expression, looking toward camera, "
        "soft natural lighting, realistic facial anatomy, "
        "plain neutral background, clearly visible face, "
        "no text or decorative elements. "
        f"Visual style: {visual_style['description']}."
    )

    if parent_id:
        prompt += (
            " The supplied reference image depicts the "
            "same fictional person at an earlier age. "
            "Use it only for recognizable genetic facial "
            "characteristics such as eye shape, nose shape, "
            "skin tone and hair texture. "
            "Do not preserve the age, height, body size, "
            "childlike facial proportions or body shape "
            "from the reference image. "
            "Apply substantial and realistic physical "
            "maturation to match the explicitly requested age. "
            "Age accuracy and physical development take "
            "priority over exact facial similarity."
        )

    if character["id"] == "boy_teenager":
        prompt += (
            " Depict an older high school student in late adolescence. "
            "Show a tall, lean athletic physique, long limbs, "
            "developed shoulders, defined cheekbones, "
            "an angular jawline and mature adolescent proportions. "
            "He must look physically close to adulthood while "
            "retaining a youthful sixteen-year-old appearance. "
            "Use a waist-up portrait to emphasize physical maturity. "
            "Avoid round baby-like cheeks, oversized childlike eyes, "
            "small childhood body proportions and prepubescent appearance."
        )

    elif character["id"] == "adult_student":
        prompt += (
            " Show six additional years of maturation "
            "from adolescence into adulthood. "
            "Fully developed masculine facial structure, "
            "broad shoulders, strong neck and athletic "
            "adult male physique. "
            "The subject must look unmistakably adult."
        )

    return prompt



def run(
    storyboard: dict,
    character_id: str | None = None,
    force: bool = False,
) -> list:

    characters = {
        character["id"]: character
        for character in storyboard["characters"]
    }

    if (
        character_id is not None
        and character_id not in characters
    ):
        raise ValueError(
            f"Unknown character: {character_id}"
        )

    provider = None

    completed = {}

    def generate(character_id: str):
        nonlocal provider

        if character_id in completed:
            return completed[character_id]

        character = characters[character_id]

        output_path = resolve_reference_path(
            character["reference_image"]
        )

        parent_id = AGE_DEPENDENCIES.get(
            character_id
        )

        dependencies = {}
        references = []

        if parent_id and parent_id in characters:
            parent_path = generate(parent_id)

            dependencies["identity_reference"] = (
                parent_path
            )

            references.append(parent_path)

        else:
            parent_id = None

        prompt = build_prompt(
            character,
            storyboard["visual_style"],
            parent_id,
        )

        parameters = {
            "prompt": prompt,
            "width": REFERENCE_WIDTH,
            "height": REFERENCE_HEIGHT,
            "seed": character["seed"],
            "provider_version": CloudflareProvider.VERSION,
        }

        key = cache.key(
            stage=STAGE,
            model=settings.image_model,
            parameters=parameters,
            dependencies=dependencies,
        )

        force_current = force and (
            selected_character is None
            or character_id == selected_character
        )

        cached = (
            not force_current
            and cache.is_valid(
                stage=STAGE,
                artifact_id=character_id,
                key=key,
                output_path=output_path,
            )
        )

        if cached:
            print(f"[CACHE HIT] {character_id}")

            logger.cache_hit(
                stage=STAGE,
                artifact_id=character_id,
                cache_key=key,
                output_path=output_path,
            )

        else:
            print(f"[GENERATING] {character_id}")

            if provider is None:
                provider = CloudflareProvider()

            provider.generate_image(
                prompt=prompt,
                width=REFERENCE_WIDTH,
                height=REFERENCE_HEIGHT,
                seed=character["seed"],
                references=references,
                output_path=output_path,
                stage=STAGE,
                artifact_id=character_id,
            )

            cache.save(
                stage=STAGE,
                artifact_id=character_id,
                key=key,
                output_path=output_path,
            )

        completed[character_id] = output_path

        print(f"  Output: {output_path}")

        return output_path

    selected_character = character_id

    if character_id:
        generate(character_id)

    else:
        for current_id in characters:
            generate(current_id)

    return list(completed.values())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate character reference portraits"
    )

    parser.add_argument(
        "--storyboard",
        default=str(settings.storyboard_path),
    )

    parser.add_argument("--character")

    parser.add_argument(
        "--force",
        action="store_true",
    )

    args = parser.parse_args()

    storyboard = load_storyboard(args.storyboard)

    run(
        storyboard,
        character_id=args.character,
        force=args.force,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
