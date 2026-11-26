from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

characters = [
    ("boy_child", "7 years old"),
    ("boy_teenager", "16 years old"),
    ("adult_student", "22 years old"),
]

before_dir = Path(
    "outputs/experiments/age_progression/before"
)

after_dir = Path("assets/references")

size = 400
padding = 20
label_height = 45

sheet = Image.new(
    "RGB",
    (size * 3 + padding * 4,
     (size + label_height) * 2 + padding * 3),
    "#181818",
)

draw = ImageDraw.Draw(sheet)

for row, (directory, label) in enumerate([
    (before_dir, "Before"),
    (after_dir, "After"),
]):
    for column, (character, age) in enumerate(characters):
        path = directory / f"{character}.png"

        with Image.open(path) as image:
            image = ImageOps.fit(
                image.convert("RGB"),
                (size, size),
            )

            x = padding + column * (size + padding)
            y = padding + row * (
                size + label_height + padding
            )

            sheet.paste(image, (x, y))

            draw.text(
                (x, y + size + 12),
                f"{label}: {age}",
                fill="white",
            )

output = Path(
    "outputs/experiments/age_progression/comparison.jpg"
)

sheet.save(output, quality=95)

print(output)
