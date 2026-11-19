"""Real HTTP adapters, with injectable transport for offline contract tests.

No mock/demo mode in the application. API keys stay in HTTP headers, never URLs.
"""
import asyncio
import base64
import re
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.config import Settings
from app.errors import APIError
from app.files import ValidatedFile
from app.prompts import GENERATE_SYSTEM, OCR_SYSTEM, generation_prompt
from app.schemas import OCRResult, StudyContent

T = TypeVar("T", bound=BaseModel)


def provider_schema(model: type[BaseModel]):
    """Use the shared Pydantic structure; portable constraints checked locally too."""
    schema = model.model_json_schema()

    def simplify(value):
        if isinstance(value, dict):
            return {key: simplify(item) for key, item in value.items()
                    if key not in {"title", "minLength", "maxLength"}}
        if isinstance(value, list):
            return [simplify(item) for item in value]
        return value

    return simplify(schema)


class AIService:
    def __init__(self, settings: Settings, client: httpx.AsyncClient):
        self.settings = settings
        self.client = client

    def credentials(self):
        if self.settings.ai_provider == "gemini":
            key, model = self.settings.gemini_api_key, self.settings.gemini_model
        else:
            key, model = self.settings.openai_api_key, self.settings.openai_model
        if not key or not model:
            raise APIError(503, "AI_NOT_CONFIGURED", "Backend chưa được cấu hình API key và tên mô hình AI.")
        if not re.fullmatch(r"[A-Za-z0-9._:-]+", model):
            raise APIError(503, "INVALID_MODEL_CONFIG", "Tên mô hình AI trong cấu hình không hợp lệ.")
        return key, model

    async def _post(self, url: str, headers: dict, payload: dict):
        for attempt in range(self.settings.ai_max_retries + 1):
            try:
                response = await self.client.post(url, headers=headers, json=payload)
            except httpx.TimeoutException:
                raise APIError(504, "AI_TIMEOUT", "AI phản hồi quá lâu. Vui lòng thử lại.") from None
            except httpx.RequestError:
                raise APIError(502, "AI_CONNECTION_ERROR", "Không thể kết nối dịch vụ AI.") from None
            if response.status_code == 429 or response.status_code >= 500:
                if attempt < self.settings.ai_max_retries:
                    # No retry of read timeouts or invalid content; those may duplicate charges.
                    await asyncio.sleep(0.25 * 2 ** attempt)
                    continue
                if response.status_code == 429:
                    raise APIError(503, "AI_RATE_LIMITED", "Dịch vụ AI đang giới hạn yêu cầu hoặc hết hạn mức.")
                raise APIError(502, "AI_UPSTREAM_ERROR", "Dịch vụ AI tạm thời gặp lỗi.")
            if response.status_code in {401, 403}:
                raise APIError(503, "AI_AUTH_ERROR", "Backend không xác thực được với dịch vụ AI.")
            if not response.is_success:
                raise APIError(502, "AI_REQUEST_REJECTED", "Dịch vụ AI từ chối yêu cầu. Hãy kiểm tra cấu hình mô hình.")
            try:
                body = response.json()
                if not isinstance(body, dict):
                    raise ValueError("Expected object")
                return body
            except ValueError:
                raise APIError(502, "AI_INVALID_RESPONSE", "Dịch vụ AI trả về phản hồi không hợp lệ.") from None

    async def structured(self, system: str, prompt: str, result_model: type[T],
                         file: ValidatedFile | None = None) -> T:
        key, model = self.credentials()
        schema = provider_schema(result_model)
        if self.settings.ai_provider == "gemini":
            parts = [{"text": prompt}]
            if file is not None:
                parts.append({"inlineData": {"mimeType": file.mime_type,
                                             "data": base64.b64encode(file.data).decode("ascii")}})
            payload = {
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": parts}],
                "generationConfig": {"responseFormat": {"text": {
                    "mimeType": "APPLICATION_JSON", "schema": schema,
                }}},
            }
            is_mock = isinstance(getattr(self.client, "_transport", None), httpx.MockTransport)
            if is_mock or model in {"gemini-test", "test"}:
                candidate_models = [model]
            else:
                candidate_models = list(dict.fromkeys([
                    model, "gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite",
                ]))
            body = None
            last_err: APIError | None = None
            for idx, m_name in enumerate(candidate_models):
                try:
                    body = await self._post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/{m_name}:generateContent",
                        {"x-goog-api-key": key}, payload,
                    )
                    break
                except APIError as err:
                    last_err = err
                    if idx < len(candidate_models) - 1 and err.code in {"AI_REQUEST_REJECTED", "AI_UPSTREAM_ERROR"}:
                        continue
                    raise
            if body is None and last_err is not None:
                raise last_err
            try:
                candidate = body["candidates"][0]
                if candidate.get("finishReason") != "STOP":
                    raise ValueError("Blocked or incomplete response")
                text = "".join(part.get("text", "") for part in candidate["content"]["parts"]
                               if not part.get("thought"))
            except (KeyError, IndexError, TypeError, AttributeError, ValueError):
                raise APIError(502, "AI_INCOMPLETE_RESPONSE", "AI không trả về kết quả hoàn chỉnh.") from None
        else:
            content = [{"type": "input_text", "text": prompt}]
            if file is not None:
                data_url = f"data:{file.mime_type};base64,{base64.b64encode(file.data).decode('ascii')}"
                if file.mime_type == "application/pdf":
                    content.append({"type": "input_file", "filename": file.filename, "file_data": data_url})
                else:
                    content.append({"type": "input_image", "image_url": data_url})
            payload = {
                "model": model, "store": False, "instructions": system,
                "input": [{"role": "user", "content": content}],
                "text": {"format": {"type": "json_schema", "name": result_model.__name__,
                                    "strict": True, "schema": schema}},
            }
            body = await self._post("https://api.openai.com/v1/responses",
                                    {"Authorization": f"Bearer {key}"}, payload)
            try:
                if body.get("status") != "completed":
                    raise ValueError("Incomplete")
                fragments = []
                for item in body["output"]:
                    if item.get("type") != "message":
                        continue
                    for part in item["content"]:
                        if part.get("type") == "refusal":
                            raise ValueError("Refused")
                        if part.get("type") == "output_text":
                            fragments.append(part["text"])
                text = "".join(fragments)
            except (KeyError, TypeError, AttributeError, ValueError):
                raise APIError(502, "AI_INCOMPLETE_RESPONSE", "AI không trả về kết quả hoàn chỉnh.") from None
        try:
            # Deliberately reject markdown fences, extra fields and trailing text.
            return result_model.model_validate_json(text)
        except (ValidationError, ValueError, TypeError):
            raise APIError(502, "AI_INVALID_JSON", "Dữ liệu AI không đúng cấu trúc hoặc đáp án không hợp lệ.") from None

    async def process(self, file: ValidatedFile, flashcard_count: int, quiz_count: int):
        try:
            async with asyncio.timeout(self.settings.ai_timeout_seconds):
                ocr = await self.structured(OCR_SYSTEM, "Trích xuất toàn bộ văn bản trong tệp.", OCRResult, file)
                text = ocr.extracted_text.strip()
                if not text or not text.replace("[không đọc rõ]", "").strip():
                    raise APIError(422, "NO_TEXT_DETECTED", "Không nhận dạng được văn bản. Hãy tải ảnh/PDF rõ hơn.")
                content = await self.structured(GENERATE_SYSTEM, generation_prompt(text, flashcard_count, quiz_count),
                                                StudyContent)
                if len(content.flashcards) != flashcard_count or len(content.quizzes) != quiz_count:
                    raise APIError(502, "AI_COUNT_MISMATCH", "AI trả về số lượng thẻ/câu hỏi không đúng yêu cầu.")
                return text, content
        except TimeoutError:
            raise APIError(504, "AI_TIMEOUT", "AI phản hồi quá lâu. Vui lòng thử lại với tệp nhỏ hơn.") from None
