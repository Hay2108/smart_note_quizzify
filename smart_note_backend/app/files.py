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

MAX_IMAGE_PIXELS = 20_000_000
MAX_IMAGE_DIMENSION = 1600
TARGET_AI_IMAGE_BYTES = 2 * 1024 * 1024
JPEG_QUALITY_STEPS = (82, 70, 55)

MIN_NATIVE_TEXT_NON_WS = 60
MIN_NATIVE_TEXT_ALNUM = 40
MIN_PAGE_TEXT_NON_WS = 20
MAX_NATIVE_TEXT_CHARS = 120_000


@dataclass(frozen=True)
class ValidatedFile:
    filename: str
    mime_type: str
    data: bytes
    native_text: str | None = None


async def read_upload(file: UploadFile, settings: Settings) -> bytes:
    parts: list[bytes] = []
    total = 0
    try:
        while chunk := await file.read(256 * 1024):
            total += len(chunk)
            if total > settings.max_upload_bytes:
                raise APIError(413, "FILE_TOO_LARGE", "Tệp vượt giới hạn dung lượng cho phép.")
            parts.append(chunk)
    finally:
        await file.close()
    if total == 0:
        raise APIError(400, "EMPTY_FILE", "Tệp rỗng. Vui lòng chọn ảnh hoặc PDF có nội dung.")
    return parts[0] if len(parts) == 1 else b"".join(parts)


def _extract_pdf_native_text(reader: PdfReader) -> str | None:
    """Extract clean selectable text from a digital PDF, or None if likely scanned."""
    num_pages = len(reader.pages)
    if num_pages == 0:
        return None
    page_texts: list[str] = []
    pages_with_text = 0
    for page in reader.pages:
        try:
            raw = page.extract_text() or ""
        except Exception:
            raw = ""
        cleaned = raw.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n").strip()
        if cleaned:
            page_texts.append(cleaned)
            if sum(1 for ch in cleaned if not ch.isspace()) >= MIN_PAGE_TEXT_NON_WS:
                pages_with_text += 1
    if not page_texts:
        return None
    # For multi-page PDFs, require at least half of pages to carry meaningful text so
    # scanned decks with only a short cover/watermark still go through Vision OCR.
    if num_pages > 1 and pages_with_text * 2 < num_pages:
        return None
    combined = "\n\n".join(page_texts)
    non_ws = sum(1 for ch in combined if not ch.isspace())
    if non_ws < MIN_NATIVE_TEXT_NON_WS:
        return None
    alnum = sum(1 for ch in combined if ch.isalnum())
    if alnum < MIN_NATIVE_TEXT_ALNUM or (alnum / non_ws) < 0.4:
        return None
    if len(combined) > MAX_NATIVE_TEXT_CHARS:
        combined = combined[:MAX_NATIVE_TEXT_CHARS].rstrip()
    return combined


def _to_rgb(image: Image.Image) -> Image.Image:
    if image.mode in ("RGBA", "LA", "PA") or (
        image.mode == "P" and "transparency" in image.info
    ):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return image if image.mode == "RGB" else image.convert("RGB")


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
            native_text = _extract_pdf_native_text(reader)
        except APIError:
            raise
        except Exception:
            raise APIError(400, "INVALID_PDF", "Không thể đọc PDF. Tệp có thể bị hỏng.") from None
        return ValidatedFile(safe_name, expected, data, native_text=native_text)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                if FORMATS.get(image.format) != expected:
                    raise ValueError("Image content differs from extension")
                if image.width * image.height > MAX_IMAGE_PIXELS:
                    raise APIError(413, "IMAGE_TOO_LARGE", "Ảnh vượt giới hạn 20 triệu điểm ảnh.")
                if getattr(image, "n_frames", 1) != 1:
                    raise APIError(415, "ANIMATED_IMAGE", "Vui lòng dùng ảnh tĩnh một khung hình.")
                # Decode once in a single open to catch truncated/corrupt payloads without double-opening.
                image.load()
                # Normalize EXIF orientation, composite alpha on white, and strip metadata on JPEG save.
                normalized = _to_rgb(ImageOps.exif_transpose(image))
                if max(normalized.size) > MAX_IMAGE_DIMENSION:
                    normalized.thumbnail(
                        (MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION),
                        Image.Resampling.LANCZOS,
                    )
                size_limit = min(settings.max_upload_bytes, TARGET_AI_IMAGE_BYTES)
                normalized_bytes = b""
                for quality in JPEG_QUALITY_STEPS:
                    output = BytesIO()
                    normalized.save(output, format="JPEG", quality=quality, optimize=True)
                    normalized_bytes = output.getvalue()
                    if len(normalized_bytes) <= size_limit:
                        break
    except APIError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise APIError(413, "IMAGE_TOO_LARGE", "Ảnh có độ phân giải quá lớn.") from None
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        raise APIError(400, "INVALID_IMAGE", "Không thể đọc ảnh hoặc nội dung ảnh không khớp định dạng.") from None
    if len(normalized_bytes) > settings.max_upload_bytes:
        raise APIError(413, "NORMALIZED_IMAGE_TOO_LARGE", "Ảnh sau chuẩn hóa quá lớn. Hãy giảm độ phân giải.")
    return ValidatedFile(safe_name, "image/jpeg", normalized_bytes)
