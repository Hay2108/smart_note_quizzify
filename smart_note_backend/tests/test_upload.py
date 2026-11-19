import json
from dataclasses import replace
from io import BytesIO
import sqlite3
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfWriter
import pytest
from sqlalchemy import text

from app.config import Settings
from app.main import create_app


def png_bytes():
    stream = BytesIO()
    Image.new("RGB", (80, 40), "white").save(stream, "PNG")
    return stream.getvalue()


def pdf_bytes(pages=1, encrypted=False):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=100, height=100)
    if encrypted:
        writer.encrypt("test-password")
    stream = BytesIO()
    writer.write(stream)
    return stream.getvalue()


CONTENT = {"flashcards": [{"front_text": "AI là gì?", "back_text": "Trí tuệ nhân tạo"}],
           "quizzes": [{"question": "AI là viết tắt của từ nào?",
                        "options": ["Artificial Intelligence", "Machine Tool", "Network", "Database"],
                        "correct_answer": "Artificial Intelligence"}]}
OCR = {"extracted_text": "AI là Artificial Intelligence, nghĩa là trí tuệ nhân tạo."}


def envelope(provider, result):
    raw = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
    if provider == "gemini":
        return {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": raw}]}}]}
    return {"status": "completed", "output": [{"type": "message", "content": [
        {"type": "output_text", "text": raw}]}]}


@pytest.fixture
def factory(tmp_path):
    apps = []

    def make(provider="gemini", replies=None, **overrides):
        calls = []
        queue = list(replies if replies is not None else [OCR, CONTENT])

        async def upstream(request):
            calls.append(request)
            if not queue:
                raise AssertionError("Unexpected AI call")
            result = queue.pop(0)
            if isinstance(result, Exception):
                raise result
            if isinstance(result, httpx.Response):
                return result
            return httpx.Response(200, json=envelope(provider, result))

        settings = Settings(database_url=f"sqlite:///{tmp_path / (str(uuid4()) + '.db')}",
                            ai_provider=provider, gemini_api_key="test-gemini-secret",
                            openai_api_key="test-openai-secret", gemini_model="gemini-test",
                            openai_model="gpt-test", ai_max_retries=0)
        settings = replace(settings, **overrides)
        app = create_app(settings, transport=httpx.MockTransport(upstream))
        apps.append(app)
        return app, calls, settings

    yield make
    for app in apps:
        app.state.engine.dispose()


def post(client, name="slide.png", data=None, mime="image/png", fields=None):
    return client.post("/api/v1/upload", files={"file": (name, png_bytes() if data is None else data, mime)},
                       data=fields or {"flashcard_count": "1", "quiz_count": "1"})


def counts(app):
    with app.state.engine.connect() as connection:
        return {table: connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
                for table in ["users", "documents", "flashcards", "quizzes", "user_progress"]}


@pytest.mark.parametrize("provider", ["gemini", "openai"])
@pytest.mark.parametrize("kind", ["image", "pdf"])
def test_upload_real_adapters_persist_linked_records(factory, provider, kind):
    app, calls, settings = factory(provider)
    with TestClient(app) as client:
        if kind == "pdf":
            response = post(client, "bai_giang.pdf", pdf_bytes(), "application/pdf")
        else:
            response = post(client, "../../bai_giang.png")
        assert response.status_code == 201, response.text
        result = response.json()
        assert result["status"] == "success"
        data = result["data"]
        assert "/" not in data["file_name"]
        assert data["extracted_text"] == OCR["extracted_text"]
        assert len(calls) == 2
        first, second = [json.loads(call.content) for call in calls]
        if provider == "gemini":
            assert calls[0].headers["x-goog-api-key"] == settings.gemini_api_key
            assert "key=" not in str(calls[0].url)
            inline = first["contents"][0]["parts"][1]["inlineData"]
            assert inline["mimeType"] == ("application/pdf" if kind == "pdf" else "image/jpeg")
            assert first["generationConfig"]["responseFormat"]["text"]["schema"]["type"] == "object"
            assert OCR["extracted_text"] in second["contents"][0]["parts"][0]["text"]
        else:
            assert calls[0].headers["authorization"] == "Bearer " + settings.openai_api_key
            part = first["input"][0]["content"][1]
            assert part["type"] == ("input_file" if kind == "pdf" else "input_image")
            assert first["text"]["format"]["strict"] is True
            assert first["store"] is False
            assert OCR["extracted_text"] in second["input"][0]["content"][0]["text"]
        assert counts(app) == {"users": 1, "documents": 1, "flashcards": 1, "quizzes": 1, "user_progress": 0}
        with app.state.engine.connect() as connection:
            doc = connection.execute(text("SELECT doc_id,user_id,file_name FROM documents")).one()
            assert doc.doc_id == data["doc_id"]
            assert doc.user_id == data["user_id"]
            for table, id_key in [("flashcards", "card_id"), ("quizzes", "quiz_id")]:
                row = connection.execute(text(f"SELECT doc_id,{id_key} FROM {table}")).one()
                assert row.doc_id == data["doc_id"]
            assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
            assert connection.execute(text("PRAGMA foreign_key_check")).all() == []
        # Request really committed and can be read through an independent SQLite connection.
        with sqlite3.connect(settings.database_url.removeprefix("sqlite:///")) as independent:
            options = independent.execute("SELECT options FROM quizzes").fetchone()[0]
            assert json.loads(options) == CONTENT["quizzes"][0]["options"]


@pytest.mark.parametrize("name,data,mime,status,code", [
    ("empty.png", b"", "image/png", 400, "EMPTY_FILE"),
    ("file.txt", b"hello", "text/plain", 415, "UNSUPPORTED_FILE_TYPE"),
    ("fake.png", b"not an image", "image/png", 400, "INVALID_IMAGE"),
    ("fake.pdf", b"not a PDF", "application/pdf", 400, "INVALID_PDF"),
    ("wrong.png", None, "application/pdf", 415, "CONTENT_TYPE_MISMATCH"),
    ("a" * 256 + ".png", None, "image/png", 400, "INVALID_FILENAME"),
])
def test_invalid_files_do_not_call_ai_or_write(factory, name, data, mime, status, code):
    app, calls, _ = factory()
    with TestClient(app) as client:
        response = post(client, name, data, mime)
        assert response.status_code == status, response.text
        assert response.json()["error"]["code"] == code
        assert calls == []
        assert not any(counts(app).values())


def test_image_bytes_cannot_be_disguised_as_another_supported_format(factory):
    app, calls, _ = factory()
    with TestClient(app) as client:
        assert post(client, "fake.jpg", png_bytes(), "image/jpeg").status_code == 400
        assert not calls


@pytest.mark.parametrize("pages,encrypted,status,code", [
    (0, False, 400, "INVALID_PDF"), (2, False, 422, "PDF_TOO_MANY_PAGES"),
    (1, True, 400, "ENCRYPTED_PDF"),
])
def test_pdf_constraints(factory, pages, encrypted, status, code):
    app, calls, _ = factory(max_pdf_pages=1)
    with TestClient(app) as client:
        response = post(client, "lesson.pdf", pdf_bytes(pages, encrypted), "application/pdf")
        assert response.status_code == status
        assert response.json()["error"]["code"] == code
        assert not calls


def test_file_limit_and_actual_chunked_body_limit(factory):
    app, calls, _ = factory(max_upload_bytes=128)
    with TestClient(app) as client:
        response = post(client, data=b"x" * 129)
        assert response.status_code == 413
        assert response.json()["error"]["code"] == "FILE_TOO_LARGE"
        # No trusted Content-Length: body is over cap before multipart parsing.
        response = client.post("/api/v1/upload", content=iter([b"x" * 600000, b"x" * 600000]),
                               headers={"Content-Type": "multipart/form-data; boundary=test"})
        assert response.status_code == 413
        assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"
        assert not calls


def test_oversized_image_pixels(factory):
    app, calls, _ = factory()
    stream = BytesIO()
    Image.new("1", (5000, 5000)).save(stream, "PNG")
    with TestClient(app) as client:
        response = post(client, data=stream.getvalue())
        assert response.status_code == 413
        assert not calls


@pytest.mark.parametrize("fields", [
    {"flashcard_count": "0"}, {"quiz_count": "21"}, {"quiz_count": "abc"}, {"user_id": "not-uuid"},
])
def test_invalid_form_fields(factory, fields):
    app, calls, _ = factory()
    with TestClient(app) as client:
        assert post(client, fields=fields).status_code == 422
        assert not calls


def test_missing_file_and_unknown_user(factory):
    app, calls, _ = factory()
    with TestClient(app) as client:
        assert client.post("/api/v1/upload").status_code == 422
        response = post(client, fields={"user_id": str(uuid4())})
        assert response.status_code == 404
        assert not calls


def test_existing_user_supported_without_local_profile(factory):
    app, calls, _ = factory()
    user_id = str(uuid4())
    with TestClient(app) as client:
        with app.state.engine.begin() as connection:
            connection.execute(text("INSERT INTO users(user_id,username) VALUES (:id,'student')"), {"id": user_id})
        response = post(client, fields={"user_id": user_id, "flashcard_count": "1", "quiz_count": "1"})
        assert response.status_code == 201
        assert response.json()["data"]["user_id"] == user_id
        assert counts(app)["users"] == 1


@pytest.mark.parametrize("provider", ["gemini", "openai"])
def test_missing_credentials_never_falls_back_to_fake_content(factory, provider):
    app, calls, _ = factory(provider, gemini_api_key="", openai_api_key="")
    with TestClient(app) as client:
        assert client.get("/health").json()["ai_configured"] is False
        response = post(client)
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "AI_NOT_CONFIGURED"
        assert not calls
        assert not any(counts(app).values())


@pytest.mark.parametrize("status,expected,code", [
    (401, 503, "AI_AUTH_ERROR"), (403, 503, "AI_AUTH_ERROR"),
    (429, 503, "AI_RATE_LIMITED"), (500, 502, "AI_UPSTREAM_ERROR"),
    (400, 502, "AI_REQUEST_REJECTED"),
])
def test_upstream_errors_redacted_and_no_db_write(factory, status, expected, code):
    secret = "secret-provider-diagnostic"
    app, _, _ = factory(replies=[httpx.Response(status, json={"error": {"message": secret}})])
    with TestClient(app) as client:
        response = post(client)
        assert response.status_code == expected
        assert response.json()["error"]["code"] == code
        assert secret not in response.text
        assert not any(counts(app).values())


@pytest.mark.parametrize("failure,expected", [
    (httpx.ReadTimeout("secret"), 504), (httpx.ConnectError("secret"), 502),
    (httpx.Response(200, content=b"not-json"), 502),
])
def test_connection_timeout_and_bad_http_json(factory, failure, expected):
    app, _, _ = factory(replies=[failure])
    with TestClient(app) as client:
        response = post(client)
        assert response.status_code == expected
        assert "secret" not in response.text
        assert not any(counts(app).values())


def test_retry_only_retryable_status(factory):
    app, calls, _ = factory(replies=[httpx.Response(429), OCR, CONTENT], ai_max_retries=1)
    with TestClient(app) as client:
        assert post(client).status_code == 201
        assert len(calls) == 3


def test_total_ai_deadline_includes_both_calls(factory):
    import asyncio
    app, _, _ = factory(ai_timeout_seconds=0.03)
    with TestClient(app) as client:
        async def delayed(*args, **kwargs):
            await asyncio.sleep(0.1)
        app.state.ai.structured = delayed
        response = post(client)
        assert response.status_code == 504
        assert response.json()["error"]["code"] == "AI_TIMEOUT"
        assert not any(counts(app).values())


def test_generation_failure_does_not_persist_ocr_as_success(factory):
    app, calls, _ = factory(replies=[OCR, httpx.Response(500)])
    with TestClient(app) as client:
        response = post(client)
        assert response.status_code == 502
        assert len(calls) == 2
        assert not any(counts(app).values())


def test_repeated_upload_reuses_local_profile(factory):
    app, _, _ = factory(replies=[OCR, CONTENT, OCR, CONTENT])
    with TestClient(app) as client:
        first, second = post(client), post(client)
        assert first.status_code == second.status_code == 201
        assert first.json()["data"]["doc_id"] != second.json()["data"]["doc_id"]
        assert counts(app) == {"users": 1, "documents": 2, "flashcards": 2, "quizzes": 2, "user_progress": 0}


@pytest.mark.parametrize("provider", ["gemini", "openai"])
def test_refusal_or_truncation_not_saved(factory, provider):
    body = ({"candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": [{"text": "{}"}]}}]}
            if provider == "gemini" else {"status": "completed", "output": [{"type": "message", "content": [
                {"type": "refusal", "refusal": "refused"}]}]})
    app, _, _ = factory(provider, replies=[httpx.Response(200, json=body)])
    with TestClient(app) as client:
        assert post(client).status_code == 502
        assert not any(counts(app).values())


@pytest.mark.parametrize("bad_result", [
    "```json\n{}\n```", {"extracted_text": 123}, {"extracted_text": "abc", "extra": "bad"},
])
def test_invalid_ocr_json_not_saved(factory, bad_result):
    app, _, _ = factory(replies=[bad_result])
    with TestClient(app) as client:
        assert post(client).status_code == 502
        assert not any(counts(app).values())


@pytest.mark.parametrize("empty", ["", "   ", "[không đọc rõ]"])
def test_no_text_is_not_fake_success(factory, empty):
    app, calls, _ = factory(replies=[{"extracted_text": empty}])
    with TestClient(app) as client:
        response = post(client)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "NO_TEXT_DETECTED"
        assert len(calls) == 1
        assert not any(counts(app).values())


@pytest.mark.parametrize("options,answer", [
    (["a", "b", "c"], "a"), (["a", "b", "c", "d"], "z"),
    (["a", "A", "c", "d"], "a"), (["a", "b", "c", "d"], "a" * 256),
])
def test_invalid_quiz_not_saved(factory, options, answer):
    content = {"flashcards": CONTENT["flashcards"], "quizzes": [
        {"question": "Question?", "options": options, "correct_answer": answer}]}
    app, _, _ = factory(replies=[OCR, content])
    with TestClient(app) as client:
        assert post(client).status_code == 502
        assert not any(counts(app).values())


def test_count_mismatch_not_saved(factory):
    app, _, _ = factory()
    with TestClient(app) as client:
        response = post(client, fields={"flashcard_count": "2", "quiz_count": "1"})
        assert response.status_code == 502
        assert response.json()["error"]["code"] == "AI_COUNT_MISMATCH"
        assert not any(counts(app).values())


def test_database_insert_failure_rolls_back_all_three_tables_and_user(factory):
    app, _, _ = factory()
    with TestClient(app) as client:
        with app.state.engine.begin() as connection:
            connection.execute(text("CREATE TRIGGER fail_quiz BEFORE INSERT ON quizzes "
                                    "BEGIN SELECT RAISE(ABORT, 'simulated write failure'); END;"))
        response = post(client)
        assert response.status_code == 500
        assert response.json()["error"]["code"] == "DATABASE_ERROR"
        assert "simulated" not in response.text
        assert not any(counts(app).values())


def test_existing_supplied_schema_is_supported_without_migration(tmp_path):
    from pathlib import Path
    import shutil
    target = tmp_path / "existing.db"
    shutil.copy2(Path(__file__).resolve().parents[1] / "smart_note.db", target)
    with sqlite3.connect(target) as connection:
        old_schema = connection.execute("SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    queue = [OCR, CONTENT]

    async def upstream(request):
        return httpx.Response(200, json=envelope("gemini", queue.pop(0)))

    settings = Settings(database_url=f"sqlite:///{target}", gemini_api_key="test", gemini_model="test")
    app = create_app(settings, transport=httpx.MockTransport(upstream))
    with TestClient(app) as client:
        assert post(client).status_code == 201
    with sqlite3.connect(target) as connection:
        assert old_schema == connection.execute("SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_swagger_docs_schema_and_cors(factory):
    app, calls, _ = factory()
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/docs").status_code == 200
        spec = client.get("/openapi.json").json()
        operation = spec["paths"]["/api/v1/upload"]["post"]
        assert "multipart/form-data" in operation["requestBody"]["content"]
        assert {"201", "400", "404", "413", "415", "422", "500", "502", "503", "504"} <= set(operation["responses"])
        assert "test-gemini-secret" not in json.dumps(spec)
        response = client.options("/api/v1/upload", headers={"Origin": "http://localhost:8501",
                                  "Access-Control-Request-Method": "POST"})
        assert response.headers["access-control-allow-origin"] == "http://localhost:8501"
        assert not calls
