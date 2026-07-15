import hashlib
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from PIL import Image

from preview_assets import (
    create_preview_asset,
    render_attachment_markdown,
    save_preview_asset,
)


def make_image_bytes(size, mode="RGB", color="red", image_format="PNG"):
    image = Image.new(mode, size, color)
    buffer = BytesIO()
    image.save(buffer, format=image_format)
    return buffer.getvalue()


class PreviewAssetTests(unittest.TestCase):
    def test_resizes_landscape_to_300_pixels_without_cropping(self):
        asset = create_preview_asset(
            make_image_bytes((600, 300)),
            display_name="Pasted image 20260710120000.jpg",
        )

        with Image.open(BytesIO(asset.jpeg_bytes)) as preview:
            self.assertEqual((300, 150), preview.size)
            self.assertEqual("RGB", preview.mode)
            self.assertEqual("JPEG", preview.format)

    def test_does_not_upscale_images_narrower_than_300_pixels(self):
        asset = create_preview_asset(
            make_image_bytes((200, 400)),
            display_name="portrait.jpg",
        )

        with Image.open(BytesIO(asset.jpeg_bytes)) as preview:
            self.assertEqual((200, 400), preview.size)

    def test_transparent_pixels_are_composited_on_white(self):
        asset = create_preview_asset(
            make_image_bytes((20, 20), mode="RGBA", color=(0, 0, 0, 0)),
            display_name="transparent.png",
        )

        with Image.open(BytesIO(asset.jpeg_bytes)) as preview:
            red, green, blue = preview.getpixel((0, 0))
            self.assertGreaterEqual(red, 245)
            self.assertGreaterEqual(green, 245)
            self.assertGreaterEqual(blue, 245)

    def test_filename_is_md5_of_saved_jpeg(self):
        asset = create_preview_asset(
            make_image_bytes((400, 200)),
            display_name="source.png",
        )

        expected_hash = hashlib.md5(asset.jpeg_bytes).hexdigest()
        self.assertEqual(f"{expected_hash}_MD5.jpg", asset.filename)

    def test_renders_existing_obsidian_open_link_and_fixed_width_embed(self):
        asset = create_preview_asset(
            make_image_bytes((400, 200)),
            display_name="Pasted image 20260710120000.jpg",
        )

        self.assertEqual(
            "\n".join(
                [
                    f"[[attachments/{asset.filename}|Open: Pasted image 20260710120000.jpg]]",
                    f"![[attachments/{asset.filename}|300]]",
                ]
            ),
            render_attachment_markdown(asset),
        )

    def test_reuses_identical_file_without_overwriting_it(self):
        asset = create_preview_asset(
            make_image_bytes((400, 200)),
            display_name="source.png",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            first_path, first_created = save_preview_asset(asset, temp_dir)
            first_mtime = Path(first_path).stat().st_mtime_ns
            second_path, second_created = save_preview_asset(asset, temp_dir)

            self.assertTrue(first_created)
            self.assertFalse(second_created)
            self.assertEqual(first_path, second_path)
            self.assertEqual(first_mtime, Path(second_path).stat().st_mtime_ns)


if __name__ == "__main__":
    unittest.main()
