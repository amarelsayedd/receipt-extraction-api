from pathlib import Path
from re import sub
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import Settings
from app.core.errors import AppError

ALLOWED_CONTENT_TYPES = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
}
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}


class FileStorageService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.upload_dir = Path(settings.upload_dir)

    async def save_upload(self, upload: UploadFile) -> tuple[Path, str, int]:
        if upload.content_type not in ALLOWED_CONTENT_TYPES:
            raise AppError(
                415,
                "unsupported_file_type",
                "Only PDF, PNG, JPG, and JPEG files are supported.",
            )
        original_name = self._safe_original_name(upload.filename)
        suffix = Path(original_name).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise AppError(415, "unsupported_file_extension", "File extension is not supported.")

        self.upload_dir.mkdir(parents=True, exist_ok=True)
        stored_name = f"{uuid4()}{suffix}"
        file_path = self.upload_dir / stored_name

        size = 0
        with file_path.open("wb") as target:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > self.settings.max_upload_size_bytes:
                    file_path.unlink(missing_ok=True)
                    raise AppError(
                        413,
                        "file_too_large",
                        "Uploaded file exceeds the configured size limit.",
                    )
                target.write(chunk)

        if size == 0:
            file_path.unlink(missing_ok=True)
            raise AppError(400, "empty_file", "Uploaded file is empty.")

        return file_path, stored_name, size

    def _safe_original_name(self, filename: str | None) -> str:
        if not filename:
            return "upload"
        name = Path(filename).name
        return sub(r"[^A-Za-z0-9._ -]", "_", name)[:255]
