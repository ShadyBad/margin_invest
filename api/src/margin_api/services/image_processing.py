"""Image validation and avatar processing service."""

from __future__ import annotations

from io import BytesIO

from PIL import Image

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALLOWED_TYPES: set[str] = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE: int = 5 * 1024 * 1024  # 5 MB
OUTPUT_SIZE: int = 256
OUTPUT_QUALITY: int = 85

# Magic byte prefixes used to verify the declared content type.
_MAGIC_BYTES: dict[str, bytes] = {
    "image/png": b"\x89PNG",
    "image/jpeg": b"\xff\xd8\xff",
    "image/webp": b"RIFF",
}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class InvalidImageError(Exception):
    """Raised when image validation fails."""


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_image(data: bytes, content_type: str) -> None:
    """Validate uploaded image data.

    Checks (in order):
    1. MIME type is in the allowed set.
    2. File size does not exceed ``MAX_SIZE``.
    3. Leading bytes match the declared MIME type.
    4. Pillow can actually open the data as an image.

    Raises ``InvalidImageError`` with a descriptive message on failure.
    """
    # 1. MIME type allowlist
    if content_type not in ALLOWED_TYPES:
        raise InvalidImageError(f"Unsupported image type: {content_type}")

    # 2. File size
    if len(data) > MAX_SIZE:
        raise InvalidImageError(
            f"File size ({len(data)} bytes) exceeds maximum ({MAX_SIZE} bytes)"
        )

    # 3. Magic-byte check
    expected_prefix = _MAGIC_BYTES[content_type]
    if not data[: len(expected_prefix)].startswith(expected_prefix):
        raise InvalidImageError(
            f"File header does not match declared content type {content_type}"
        )

    # 4. Pillow decode check
    try:
        img = Image.open(BytesIO(data))
        img.verify()
    except Exception:
        raise InvalidImageError("Data is not a valid image")


# ---------------------------------------------------------------------------
# Processing
# ---------------------------------------------------------------------------


def process_avatar(data: bytes) -> bytes:
    """Convert image data to a 256x256 WebP avatar.

    Steps:
    1. Open the image with Pillow.
    2. Center-crop to a square.
    3. Resize to ``OUTPUT_SIZE x OUTPUT_SIZE`` using Lanczos resampling.
    4. Encode as WebP at ``OUTPUT_QUALITY`` quality.

    Returns the WebP-encoded bytes.
    """
    img = Image.open(BytesIO(data))
    img = img.convert("RGB")

    width, height = img.size

    # Center crop to square
    if width != height:
        side = min(width, height)
        left = (width - side) // 2
        top = (height - side) // 2
        right = left + side
        bottom = top + side
        img = img.crop((left, top, right, bottom))

    # Resize to output dimensions
    img = img.resize((OUTPUT_SIZE, OUTPUT_SIZE), Image.LANCZOS)

    # Encode as WebP
    buf = BytesIO()
    img.save(buf, format="WEBP", quality=OUTPUT_QUALITY)
    return buf.getvalue()
