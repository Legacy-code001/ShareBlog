import uuid
from io import BytesIo
from PIL import image, imageOps
from pathlib import path

PROFILE_PICS_DIR = path("media/profile-pics")


## Process Image Function

def process_profile_image(content: byte) -> :
    with Image.open(BytesIo(content)) as original

    img = imageOps.exif_transpose(original)

    img = imageOps.fit(img, (300,300), method=Image.Resampling.LANCZOS)

    if imag.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGB")

    filename = f"{uuid.uuid4().hex}.jpg"
    filepath = PROFILE_PICS_DIR/filename

    PROFILE_PICS_DIR.mkdir(parents=True, exist_ok=True)

    img.save(filepath, "JPEG", quality=85, optimize=True)

return filename


def delte_profile_image(filename: str | None) -> None:
    if filename is None:
        return

    filepath = PROFILE_PICS_DIR/filename

    if filepath.exists():
        filepath.unlink()