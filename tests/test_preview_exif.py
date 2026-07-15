import unittest
from io import BytesIO

from PIL import Image

from preview_assets import create_preview_asset


class PreviewExifTests(unittest.TestCase):
    def test_applies_exif_orientation_before_resizing(self):
        source = Image.new("RGB", (100, 200), "blue")
        exif = Image.Exif()
        exif[274] = 6
        source_bytes = BytesIO()
        source.save(source_bytes, format="JPEG", exif=exif)

        asset = create_preview_asset(source_bytes.getvalue(), "rotated.jpg")

        with Image.open(BytesIO(asset.jpeg_bytes)) as preview:
            self.assertEqual((200, 100), preview.size)


if __name__ == "__main__":
    unittest.main()
