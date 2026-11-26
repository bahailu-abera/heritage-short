
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps


def create_contact_sheet(
    files,
    output,
    width=480,
    height=270,
    columns=2,
):
    padding = 15
    label_height = 40

    rows = (len(files) + columns - 1) // columns

    sheet = Image.new(
        "RGB",
        (
            columns * (width + padding) + padding,
            rows * (height + label_height + padding)
            + padding,
        ),
        "#181818",
    )

    draw = ImageDraw.Draw(sheet)

    for index, path in enumerate(files):
        with Image.open(path) as image:
            image = ImageOps.contain(
                image.convert("RGB"),
                (width, height),
            )

            x = padding + (
                index % columns
            ) * (width + padding)

            y = padding + (
                index // columns
            ) * (height + label_height + padding)

            sheet.paste(image, (x, y))

            draw.text(
                (x, y + height + 10),
                path.stem,
                fill="white",
            )

    output.parent.mkdir(
        parents=True, exist_ok=True
    )

    sheet.save(output, quality=95)

    print(f"Contact sheet: {output}")


if __name__ == "__main__":
    create_contact_sheet(
        files=sorted(
            Path("outputs/keyframes").glob("shot_*.png")
        ),
        output=Path(
            "outputs/drafts/keyframe_contact_sheet.jpg"
        ),
    )

    create_contact_sheet(
        files=[
            Path("assets/references/boy_child.png"),
            Path("assets/references/boy_teenager.png"),
            Path("assets/references/adult_student.png"),
            Path("assets/references/mother.png"),
        ],
        output=Path(
            "outputs/drafts/character_contact_sheet.jpg"
        ),
        width=400,
        height=400,
        columns=4,
    )
