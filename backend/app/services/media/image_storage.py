import uuid
from pathlib import Path

from app.core.config import get_settings
from app.core.exceptions import ValidationAppError

# Signature-sniffed rather than trusting the client's Content-Type, so a
# renamed non-image can't be stored and served from /media.
_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"\xff\xd8\xff", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", ".png"),
)


def _detect_extension(data: bytes) -> str | None:
    for signature, extension in _SIGNATURES:
        if data.startswith(signature):
            return extension
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return None


class ImageStorage:
    """Local-filesystem image store. Files are written under
    `settings.media_root/<folder>/` with a random name and exposed at
    `settings.media_url_prefix/<folder>/<name>` (mounted in app/main.py)."""

    def __init__(self, folder: str) -> None:
        settings = get_settings()
        self.folder = folder
        self.directory = Path(settings.media_root) / folder
        self.url_prefix = f"{settings.media_url_prefix.rstrip('/')}/{folder}"
        self.max_bytes = settings.max_image_upload_bytes

    def save(self, data: bytes) -> str:
        """Validates and stores the image, returning its public URL path."""
        if not data:
            raise ValidationAppError("Image file is empty")
        if len(data) > self.max_bytes:
            raise ValidationAppError(
                f"Image exceeds the {self.max_bytes // (1024 * 1024)} MB upload limit"
            )
        extension = _detect_extension(data)
        if extension is None:
            raise ValidationAppError("Image must be a JPEG, PNG, or WebP file")

        self.directory.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid.uuid4().hex}{extension}"
        (self.directory / filename).write_bytes(data)
        return f"{self.url_prefix}/{filename}"

    def delete(self, url: str | None) -> None:
        """Best-effort removal of a file this store previously returned.
        URLs outside this store's prefix are ignored."""
        if not url or not url.startswith(f"{self.url_prefix}/"):
            return
        name = url.removeprefix(f"{self.url_prefix}/")
        if "/" in name or "\\" in name or name.startswith("."):
            return
        (self.directory / name).unlink(missing_ok=True)


def menu_image_storage() -> ImageStorage:
    return ImageStorage("menu")
