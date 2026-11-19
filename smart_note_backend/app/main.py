from contextlib import asynccontextmanager
import time
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import FastAPI, File, Form, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text as sql_text
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.ai import AIService
from app.config import Settings
from app.database import Base, make_database
from app.errors import APIError, error_body
from app.files import read_upload, validate_file
from app.repository import check_user, save_study_material
from app.schemas import ErrorResponse, UploadResponse


class UploadBodyLimit:
    """Bound the actual HTTP body before multipart parsing, including chunked uploads.

    The file-specific limit is checked again after parsing. One MiB is reserved for
    multipart headers and fields. Replays buffered chunks directly without copying
    into a single bytes object and releases chunk references as they are consumed.
    """
    def __init__(self, app, max_bytes: int):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "POST" or scope["path"].rstrip("/") != "/api/v1/upload":
            return await self.app(scope, receive, send)
        for key, value in scope.get("headers", ()):
            if key == b"content-length":
                try:
                    if int(value) > self.max_bytes:
                        response = JSONResponse(status_code=413, content=error_body(
                            "REQUEST_TOO_LARGE", "Yêu cầu tải lên vượt giới hạn dung lượng cho phép."))
                        return await response(scope, receive, send)
                except ValueError:
                    pass
                break
        chunks: list[bytes] = []
        total = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if chunk:
                total += len(chunk)
                if total > self.max_bytes:
                    chunks.clear()
                    response = JSONResponse(status_code=413, content=error_body(
                        "REQUEST_TOO_LARGE", "Yêu cầu tải lên vượt giới hạn dung lượng cho phép."))
                    return await response(scope, receive, send)
                chunks.append(chunk)
            if not message.get("more_body", False):
                break

        index = 0
        total_chunks = len(chunks)
        done = False

        async def replay():
            nonlocal index, done
            if not done:
                if total_chunks == 0:
                    done = True
                    return {"type": "http.request", "body": b"", "more_body": False}
                body_chunk = chunks[index]
                chunks[index] = b""
                index += 1
                more = index < total_chunks
                if not more:
                    done = True
                    chunks.clear()
                return {"type": "http.request", "body": body_chunk, "more_body": more}
            return await receive()

        return await self.app(scope, replay, send)


def create_app(settings: Settings | None = None, *, transport: httpx.AsyncBaseTransport | None = None):
    settings = settings or Settings.from_env()
    engine, session_factory = make_database(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await run_in_threadpool(Base.metadata.create_all, engine)
        async with httpx.AsyncClient(timeout=httpx.Timeout(settings.ai_timeout_seconds, connect=10),
                                     transport=transport, follow_redirects=False) as client:
            app.state.ai = AIService(settings, client)
            yield
        engine.dispose()

    app = FastAPI(
        title="Smart Note & Quizzify Upload API", version="1.0.0",
        description="Upload ảnh/PDF → AI OCR → tạo flashcard/quiz → lưu SQLite. API dành cho MVP chạy cục bộ.",
        lifespan=lifespan,
    )
    app.state.session_factory = session_factory
    app.state.engine = engine
    app.add_middleware(UploadBodyLimit, max_bytes=settings.max_upload_bytes + 1024 * 1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        expose_headers=["X-Process-Time-Ms"],
    )

    @app.exception_handler(APIError)
    async def api_error(_, exc):
        return JSONResponse(status_code=exc.status_code, content=error_body(exc.code, exc.message))

    @app.exception_handler(RequestValidationError)
    async def validation_error(_, exc):
        # Do not echo uploaded bytes, raw AI text, secrets or internal exception context.
        return JSONResponse(status_code=422, content=error_body(
            "INVALID_REQUEST", "Thiếu tệp hoặc tham số không hợp lệ. Kiểm tra biểu mẫu trong /docs."))

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_, exc):
        return JSONResponse(status_code=exc.status_code, content=error_body(
            "HTTP_ERROR", "Không thể xử lý yêu cầu HTTP. Kiểm tra đường dẫn và định dạng multipart/form-data."))

    @app.exception_handler(SQLAlchemyError)
    async def database_error(_, exc):
        return JSONResponse(status_code=500, content=error_body(
            "DATABASE_ERROR", "Không thể lưu dữ liệu. Giao dịch đã được hủy, vui lòng thử lại."))

    @app.get("/health", tags=["System"], summary="Kiểm tra API và kết nối SQLite")
    def health():
        with engine.connect() as connection:
            connection.execute(sql_text("SELECT 1"))
        return {"status": "ok", "database": "ok", "ai_provider": settings.ai_provider,
                "ai_configured": bool(
                    settings.gemini_api_key and settings.gemini_model if settings.ai_provider == "gemini"
                    else settings.openai_api_key and settings.openai_model
                )}

    @app.post(
        "/api/v1/upload", status_code=201, response_model=UploadResponse, tags=["Upload"],
        summary="Nhận ảnh/PDF, gọi AI và lưu tài liệu cùng flashcard/quiz",
        description="Gửi một file JPG/JPEG/PNG/WEBP/PDF (mặc định tối đa 10 MiB, PDF tối đa 20 trang). "
                    "Trả 201 sau khi toàn bộ dữ liệu đã được lưu. Không cần gửi API key từ Frontend. "
                    "Bỏ user_id để sử dụng hồ sơ cục bộ; user_id được gửi phải tồn tại. "
                    "Tác vụ đồng bộ có thể mất tới AI_TIMEOUT_SECONDS, không cam kết hoàn tất dưới 3 giây.",
        responses={code: {"model": ErrorResponse, "description": description} for code, description in {
            400: "Tệp rỗng/hỏng, tên tệp không hợp lệ hoặc PDF mã hóa",
            404: "Không tìm thấy user_id", 413: "Tệp hoặc ảnh vượt giới hạn",
            415: "Định dạng không hỗ trợ hoặc MIME không khớp", 422: "Tham số sai, quá số trang hoặc không có chữ",
            500: "Lỗi lưu SQLite; rollback", 502: "AI lỗi hoặc JSON không hợp lệ",
            503: "Chưa cấu hình AI, lỗi xác thực hoặc hết hạn mức", 504: "AI timeout",
        }.items()},
    )
    async def upload(
        response: Response,
        file: Annotated[UploadFile, File(description="Một ảnh JPG/JPEG/PNG/WEBP hoặc PDF")],
        user_id: Annotated[UUID | None, Form(description="UUID người dùng đã tồn tại; bỏ trống để dùng hồ sơ cục bộ")] = None,
        flashcard_count: Annotated[int, Form(ge=1, le=20, description="Số flashcard cần tạo")] = 5,
        quiz_count: Annotated[int, Form(ge=1, le=20, description="Số câu trắc nghiệm, mỗi câu 4 lựa chọn")] = 5,
    ):
        started = time.perf_counter()
        filename, content_type = file.filename, file.content_type
        data = await read_upload(file, settings)
        validated = await run_in_threadpool(validate_file, filename, content_type, data, settings)
        del data
        if user_id is not None:
            await run_in_threadpool(check_user, session_factory, user_id)
        text, content = await app.state.ai.process(validated, flashcard_count, quiz_count)
        result = await run_in_threadpool(save_study_material, session_factory, validated.filename, text, content, user_id)
        response.headers["X-Process-Time-Ms"] = str(round((time.perf_counter() - started) * 1000))
        return result

    return app


app = create_app()
