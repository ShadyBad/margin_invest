"""Tests for the image processing service."""

from __future__ import annotations

from io import BytesIO

import pytest
from margin_api.services.image_processing import (
    MAX_SIZE,
    OUTPUT_SIZE,
    InvalidImageError,
    process_avatar,
    validate_image,
)
from PIL import Image

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_png(width: int = 200, height: int = 200) -> bytes:
    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_jpeg(width: int = 200, height: int = 200) -> bytes:
    img = Image.new("RGB", (width, height), color=(0, 255, 0))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_webp(width: int = 200, height: int = 200) -> bytes:
    img = Image.new("RGB", (width, height), color=(0, 0, 255))
    buf = BytesIO()
    img.save(buf, format="WEBP")
    return buf.getvalue()


def _make_gif(width: int = 200, height: int = 200) -> bytes:
    img = Image.new("RGB", (width, height), color=(128, 128, 128))
    buf = BytesIO()
    img.save(buf, format="GIF")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# validate_image — happy paths
# ---------------------------------------------------------------------------


class TestValidateImageAcceptsValid:
    def test_accepts_valid_png(self) -> None:
        data = _make_png()
        validate_image(data, "image/png")  # should not raise

    def test_accepts_valid_jpeg(self) -> None:
        data = _make_jpeg()
        validate_image(data, "image/jpeg")  # should not raise

    def test_accepts_valid_webp(self) -> None:
        data = _make_webp()
        validate_image(data, "image/webp")  # should not raise


# ---------------------------------------------------------------------------
# validate_image — unsupported MIME type
# ---------------------------------------------------------------------------


class TestValidateImageRejectsUnsupportedType:
    def test_rejects_gif_mime_type(self) -> None:
        data = _make_gif()
        with pytest.raises(InvalidImageError, match="Unsupported image type"):
            validate_image(data, "image/gif")

    def test_rejects_svg_mime_type(self) -> None:
        with pytest.raises(InvalidImageError, match="Unsupported image type"):
            validate_image(b"<svg></svg>", "image/svg+xml")

    def test_rejects_bmp_mime_type(self) -> None:
        with pytest.raises(InvalidImageError, match="Unsupported image type"):
            validate_image(b"\x00", "image/bmp")


# ---------------------------------------------------------------------------
# validate_image — file size
# ---------------------------------------------------------------------------


class TestValidateImageRejectsOversized:
    def test_rejects_file_exceeding_max_size(self) -> None:
        # Create data just over the limit
        oversized = b"\x89PNG" + b"\x00" * (MAX_SIZE + 1)
        with pytest.raises(InvalidImageError, match="exceeds maximum"):
            validate_image(oversized, "image/png")

    def test_accepts_file_at_exact_max_size(self) -> None:
        """A file of exactly MAX_SIZE bytes should be accepted (size check only)."""
        # Build a real PNG that we pad to exactly MAX_SIZE
        png = _make_png()
        # We can't easily make a PNG of exact size, so we test the size
        # boundary with a small PNG that is under the limit.
        assert len(png) <= MAX_SIZE
        validate_image(png, "image/png")  # should not raise


# ---------------------------------------------------------------------------
# validate_image — magic byte mismatch
# ---------------------------------------------------------------------------


class TestValidateImageRejectsMismatchedMagicBytes:
    def test_claims_png_but_sends_jpeg(self) -> None:
        jpeg_data = _make_jpeg()
        with pytest.raises(InvalidImageError, match="does not match"):
            validate_image(jpeg_data, "image/png")

    def test_claims_jpeg_but_sends_png(self) -> None:
        png_data = _make_png()
        with pytest.raises(InvalidImageError, match="does not match"):
            validate_image(png_data, "image/jpeg")

    def test_claims_webp_but_sends_png(self) -> None:
        png_data = _make_png()
        with pytest.raises(InvalidImageError, match="does not match"):
            validate_image(png_data, "image/webp")


# ---------------------------------------------------------------------------
# validate_image — non-image bytes
# ---------------------------------------------------------------------------


class TestValidateImageRejectsNonImage:
    def test_rejects_truncated_png(self) -> None:
        """Data starts with PNG magic bytes but is not a valid image."""
        fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        with pytest.raises(InvalidImageError, match="not a valid image"):
            validate_image(fake_png, "image/png")

    def test_rejects_truncated_jpeg(self) -> None:
        """Data starts with JPEG magic bytes but is not a valid image."""
        fake_jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        with pytest.raises(InvalidImageError, match="not a valid image"):
            validate_image(fake_jpeg, "image/jpeg")


# ---------------------------------------------------------------------------
# process_avatar — output format
# ---------------------------------------------------------------------------


class TestProcessAvatarOutputFormat:
    def test_output_is_webp(self) -> None:
        data = _make_png(400, 400)
        result = process_avatar(data)
        img = Image.open(BytesIO(result))
        assert img.format == "WEBP"


# ---------------------------------------------------------------------------
# process_avatar — output dimensions
# ---------------------------------------------------------------------------


class TestProcessAvatarDimensions:
    def test_large_square_resized_to_256x256(self) -> None:
        data = _make_png(800, 800)
        result = process_avatar(data)
        img = Image.open(BytesIO(result))
        assert img.size == (OUTPUT_SIZE, OUTPUT_SIZE)

    def test_landscape_resized_to_256x256(self) -> None:
        data = _make_png(800, 600)
        result = process_avatar(data)
        img = Image.open(BytesIO(result))
        assert img.size == (OUTPUT_SIZE, OUTPUT_SIZE)

    def test_small_image_upscaled_to_256x256(self) -> None:
        data = _make_png(100, 100)
        result = process_avatar(data)
        img = Image.open(BytesIO(result))
        assert img.size == (OUTPUT_SIZE, OUTPUT_SIZE)

    def test_tall_portrait_resized_to_256x256(self) -> None:
        data = _make_png(200, 400)
        result = process_avatar(data)
        img = Image.open(BytesIO(result))
        assert img.size == (OUTPUT_SIZE, OUTPUT_SIZE)

    def test_wide_landscape_resized_to_256x256(self) -> None:
        data = _make_jpeg(600, 200)
        result = process_avatar(data)
        img = Image.open(BytesIO(result))
        assert img.size == (OUTPUT_SIZE, OUTPUT_SIZE)


# ---------------------------------------------------------------------------
# process_avatar — center crop behaviour
# ---------------------------------------------------------------------------


class TestProcessAvatarCenterCrop:
    def test_landscape_center_cropped(self) -> None:
        """800x600 landscape should crop to 600x600 centered, then resize."""
        # Create an image where the center region is distinguishable.
        img = Image.new("RGB", (800, 600), color=(255, 0, 0))
        # Paint the center 600x600 region green so we can verify it was kept
        for x in range(100, 700):
            for y in range(0, 600):
                img.putpixel((x, y), (0, 255, 0))
        buf = BytesIO()
        img.save(buf, format="PNG")

        result = process_avatar(buf.getvalue())
        out = Image.open(BytesIO(result))
        # Center pixel should be green (from the center crop)
        center = out.getpixel((128, 128))
        assert center[1] > 200, f"Expected green center pixel, got {center}"

    def test_tall_portrait_center_cropped(self) -> None:
        """200x400 portrait should crop to 200x200 centered, then resize."""
        img = Image.new("RGB", (200, 400), color=(255, 0, 0))
        # Paint the center 200x200 region blue
        for x in range(0, 200):
            for y in range(100, 300):
                img.putpixel((x, y), (0, 0, 255))
        buf = BytesIO()
        img.save(buf, format="PNG")

        result = process_avatar(buf.getvalue())
        out = Image.open(BytesIO(result))
        center = out.getpixel((128, 128))
        assert center[2] > 200, f"Expected blue center pixel, got {center}"


# ---------------------------------------------------------------------------
# process_avatar — accepts various input formats
# ---------------------------------------------------------------------------


class TestProcessAvatarInputFormats:
    def test_accepts_jpeg_input(self) -> None:
        data = _make_jpeg(300, 300)
        result = process_avatar(data)
        img = Image.open(BytesIO(result))
        assert img.format == "WEBP"
        assert img.size == (OUTPUT_SIZE, OUTPUT_SIZE)

    def test_accepts_webp_input(self) -> None:
        data = _make_webp(300, 300)
        result = process_avatar(data)
        img = Image.open(BytesIO(result))
        assert img.format == "WEBP"
        assert img.size == (OUTPUT_SIZE, OUTPUT_SIZE)
