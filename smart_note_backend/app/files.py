from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePosixPath
import warnings

from fastapi import UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from pypdf import PdfReader

from app.config import Settings
from app.errors import APIError

EXTENSIONS = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
              ".webp": "image/webp", ".pdf": "application/pdf"}
FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


@dataclass(frozen=True)
class ValidatedFile:
    filename: str
    mime_type: str
    data: bytes


async def read_upload(file: UploadFile, settings: Settings) -> bytes:
    chunks = bytearray()
    try:
        while chunk := await file.read(64 * 1024):
            chunks.extend(chunk)
            if len(chunks) > settings.max_upload_bytes:
                raise APIError(413, "FILE_TOO_LARGE", "Tệp vượt giới hạn dung lượng cho phép.")
    finally:
        await file.close()
    if not chunks:
        raise APIError(400, "EMPTY_FILE", "Tệp rỗng. Vui lòng chọn ảnh hoặc PDF có nội dung.")
    return bytes(chunks)


def validate_file(filename: str | None, content_type: str | None, data: bytes,
                  settings: Settings) -> ValidatedFile:
    # Name is metadata only: never create a server path from an uploaded name.
    safe_name = PurePosixPath((filename or "").replace("\\", "/")).name
    if not safe_name or len(safe_name) > 255 or any(ord(c) < 32 for c in safe_name):
        raise APIError(400, "INVALID_FILENAME", "Tên tệp không hợp lệ hoặc dài hơn 255 ký tự.")
    expected = EXTENSIONS.get(PurePosixPath(safe_name).suffix.lower())
    if expected is None:
        raise APIError(415, "UNSUPPORTED_FILE_TYPE", "Chỉ hỗ trợ JPG, JPEG, PNG, WEBP và PDF.")
    claimed = (content_type or "application/octet-stream").split(";")[0].strip().lower()
    if claimed not in {expected, "application/octet-stream"}:
        raise APIError(415, "CONTENT_TYPE_MISMATCH", "Loại nội dung không khớp phần mở rộng của tệp.")
    if expected == "application/pdf":
        try:
            if not data.startswith(b"%PDF-"):
                raise ValueError("Missing PDF header")
            reader = PdfReader(BytesIO(data), strict=True)
            if reader.is_encrypted:
                raise APIError(400, "ENCRYPTED_PDF", "PDF có mật khẩu. Vui lòng tải bản không mã hóa.")
            if len(reader.pages) == 0:
                raise ValueError("No pages")
            if len(reader.pages) > settings.max_pdf_pages:
                raise APIError(422, "PDF_TOO_MANY_PAGES",
                               f"PDF vượt giới hạn {settings.max_pdf_pages} trang. Hãy chia nhỏ tệp.")
        except APIError:
            raise
        except Exception:
            raise APIError(400, "INVALID_PDF", "Không thể đọc PDF. Tệp có thể bị hỏng.") from None
        return ValidatedFile(safe_name, expected, data)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                if FORMATS.get(image.format) != expected:
                    raise ValueError("Image content differs from extension")
                if image.width * image.height > 20_000_000:
                    raise APIError(413, "IMAGE_TOO_LARGE", "Ảnh vượt giới hạn 20 triệu điểm ảnh.")
                if getattr(image, "n_frames", 1) != 1:
                    raise APIError(415, "ANIMATED_IMAGE", "Vui lòng dùng ảnh tĩnh một khung hình.")
                image.verify()
            # Normalize EXIF orientation and strip metadata before external transmission.
            with Image.open(BytesIO(data)) as image:
                normalized = ImageOps.exif_transpose(image).convert("RGB")
                output = BytesIO()
                normalized.save(output, format="JPEG", quality=95)
    except APIError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise APIError(413, "IMAGE_TOO_LARGE", "Ảnh có độ phân giải quá lớn.") from None
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        raise APIError(400, "INVALID_IMAGE", "Không thể đọc ảnh hoặc nội dung ảnh không khớp định dạng.") from None
    normalized_bytes = output.getvalue()
    if len(normalized_bytes) > settings.max_upload_bytes:
        raise APIError(413, "NORMALIZED_IMAGE_TOO_LARGE", "Ảnh sau chuẩn hóa quá lớn. Hãy giảm độ phân giải.")
    return ValidatedFile(safe_name, "image/jpeg", normalized_bytes)
