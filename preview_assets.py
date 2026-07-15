import hashlib
import os
import re
from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageOps


MAX_PREVIEW_WIDTH = 300
JPEG_QUALITY = 85


@dataclass(frozen=True)
class PreviewAsset:
    filename: str
    display_name: str
    jpeg_bytes: bytes


def _safe_display_name(display_name: str) -> str:
    cleaned = re.sub(r"[\[\]|\r\n]+", " ", str(display_name or ""))
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or "Pasted image.jpg"


def _to_rgb(image: Image.Image) -> Image.Image:
    if image.mode in ("RGBA", "LA") or "transparency" in image.info:
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, "white")
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return image.convert("RGB")


def create_preview_asset(
    image_bytes: bytes,
    display_name: str,
    max_width: int = MAX_PREVIEW_WIDTH,
) -> PreviewAsset:
    if max_width <= 0:
        raise ValueError("max_width должен быть больше нуля")

    with Image.open(BytesIO(image_bytes)) as source:
        image = ImageOps.exif_transpose(source)
        image.load()

        if image.width > max_width:
            target_height = max(1, round(image.height * max_width / image.width))
            image = image.resize(
                (max_width, target_height),
                Image.Resampling.LANCZOS,
            )

        rgb_image = _to_rgb(image)
        output = BytesIO()
        rgb_image.save(
            output,
            format="JPEG",
            quality=JPEG_QUALITY,
            optimize=True,
        )

    jpeg_bytes = output.getvalue()
    digest = hashlib.md5(jpeg_bytes).hexdigest()
    return PreviewAsset(
        filename=f"{digest}_MD5.jpg",
        display_name=_safe_display_name(display_name),
        jpeg_bytes=jpeg_bytes,
    )


def save_preview_asset(asset: PreviewAsset, attachments_path: str) -> tuple[str, bool]:
    os.makedirs(attachments_path, exist_ok=True)
    file_path = os.path.join(attachments_path, asset.filename)

    try:
        with open(file_path, "xb") as file:
            file.write(asset.jpeg_bytes)
        created = True
    except FileExistsError:
        created = False
    except Exception:
        try:
            os.remove(file_path)
        except OSError:
            pass
        raise

    if created:
        try:
            os.chmod(file_path, 0o666)
        except OSError:
            pass

    return file_path, created


def render_attachment_markdown(asset: PreviewAsset) -> str:
    target = f"attachments/{asset.filename}"
    return "\n".join(
        [
            f"[[{target}|Open: {asset.display_name}]]",
            f"![[{target}|{MAX_PREVIEW_WIDTH}]]",
        ]
    )
