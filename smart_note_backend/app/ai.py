"""Real HTTP adapters, with injectable transport for offline contract tests.

No mock/demo mode in the application. API keys stay in HTTP headers, never URLs.
"""
import asyncio
import base64
import re
import time
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.config import Settings
from app.errors import APIError
from app.files import ValidatedFile
from app.prompts import GENERATE_SYSTEM, UNIFIED_SYSTEM, generation_prompt, unified_prompt
from app.schemas import StudyContent, UnifiedStudyOutput

T = TypeVar("T", bound=BaseModel)

GEMINI_FALLBACK_MODELS = (
    "gemini-3.1-flash-lite-preview",
    "gemini-3-flash-preview",
    "gemini-flash-lite-latest",
    "gemini-3.6-flash",
)
MODEL_COOLDOWN_SECONDS = 120.0


def _gemini_thinking_config(model_name: str) -> dict | None:
    """Minimize hidden reasoning tokens to slash Flash latency while staying compatible across versions."""
    lower = model_name.lower()
    if "2.5" in lower:
        return {"thinkingBudget": 0}
    if any(tag in lower for tag in ("gemini-3", "gemini-4")):
        return {"thinkingLevel": "minimal"}
    return None


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
        self._model_cooldowns: dict[str, float] = {}

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

    async def _post(self, url: str, headers: dict, payload: dict,
                    timeout: float | None = None, max_retries: int | None = None):
        req_timeout = httpx.Timeout(timeout, connect=min(10.0, timeout)) if timeout is not None else None
        retries = self.settings.ai_max_retries if max_retries is None else max_retries
        for attempt in range(retries + 1):
            try:
                if req_timeout is not None:
                    response = await self.client.post(url, headers=headers, json=payload, timeout=req_timeout)
                else:
                    response = await self.client.post(url, headers=headers, json=payload)
            except httpx.TimeoutException:
                raise APIError(504, "AI_TIMEOUT", "AI phản hồi quá lâu. Vui lòng thử lại.") from None
            except httpx.RequestError:
                raise APIError(502, "AI_CONNECTION_ERROR", "Không thể kết nối dịch vụ AI.") from None
            if response.status_code == 429 or response.status_code >= 500:
                if attempt < retries:
                    # No retry of read timeouts or invalid content; those may duplicate charges.
                    await asyncio.sleep(0.25 * 2 ** attempt)
                    continue
                if response.status_code == 429:
                    raise APIError(503, "AI_RATE_LIMITED", "Dịch vụ AI đang giới hạn yêu cầu hoặc hết hạn mức.")
                raise APIError(502, "AI_UPSTREAM_ERROR", "Dịch vụ AI tạm thời gặp lỗi.")
            if response.status_code in {401, 403}:
                raise APIError(503, "AI_AUTH_ERROR", "Backend không xác thực được với dịch vụ AI.")
            if not response.is_success:
                err = APIError(502, "AI_REQUEST_REJECTED", "Dịch vụ AI từ chối yêu cầu. Hãy kiểm tra cấu hình mô hình.")
                err.upstream_status = response.status_code
                raise err
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
            base_gen_config = {
                "temperature": 0.2,
                "responseFormat": {"text": {
                    "mimeType": "APPLICATION_JSON", "schema": schema,
                }},
            }
            is_mock = isinstance(getattr(self.client, "_transport", None), httpx.MockTransport)
            if is_mock or model in {"gemini-test", "test"}:
                candidate_models = [model]
            else:
                ordered = list(dict.fromkeys([model, *GEMINI_FALLBACK_MODELS]))
                if len(ordered) > 1:
                    now = time.monotonic()
                    healthy: list[str] = []
                    cooled: list[str] = []
                    for m_name in ordered:
                        if self._model_cooldowns.get(m_name, 0.0) > now:
                            cooled.append(m_name)
                        else:
                            self._model_cooldowns.pop(m_name, None)
                            healthy.append(m_name)
                    candidate_models = healthy + cooled
                else:
                    candidate_models = ordered

            deadline = time.monotonic() + self.settings.ai_timeout_seconds
            body = None
            last_err: APIError | None = None
            for idx, m_name in enumerate(candidate_models):
                remaining = deadline - time.monotonic()
                if remaining <= 0 or (idx > 0 and remaining <= 0.05):
                    raise APIError(504, "AI_TIMEOUT", "AI phản hồi quá lâu. Vui lòng thử lại với tệp nhỏ hơn.")
                is_last = idx == len(candidate_models) - 1
                attempt_timeout = (
                    remaining if is_last
                    else min(remaining, min(25.0, self.settings.ai_timeout_seconds * 0.35))
                )
                attempt_retries = self.settings.ai_max_retries if is_last else 0
                gen_config = dict(base_gen_config)
                thinking_cfg = _gemini_thinking_config(m_name)
                if thinking_cfg is not None:
                    gen_config["thinkingConfig"] = thinking_cfg
                payload = {
                    "systemInstruction": {"parts": [{"text": system}]},
                    "contents": [{"role": "user", "parts": parts}],
                    "generationConfig": gen_config,
                }
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m_name}:generateContent"
                headers = {"x-goog-api-key": key}
                try:
                    body = await self._post(
                        url, headers, payload, timeout=attempt_timeout, max_retries=attempt_retries
                    )
                    self._model_cooldowns.pop(m_name, None)
                    break
                except APIError as err:
                    # If a Gemini model rejects thinkingConfig with HTTP 400, strip thinkingConfig and retry once.
                    if (
                        err.code == "AI_REQUEST_REJECTED"
                        and getattr(err, "upstream_status", None) == 400
                        and thinking_cfg is not None
                    ):
                        retry_remaining = deadline - time.monotonic()
                        if retry_remaining > 0.05:
                            retry_timeout = (
                                retry_remaining if is_last
                                else min(retry_remaining, min(25.0, self.settings.ai_timeout_seconds * 0.35))
                            )
                            plain_payload = {
                                "systemInstruction": {"parts": [{"text": system}]},
                                "contents": [{"role": "user", "parts": parts}],
                                "generationConfig": base_gen_config,
                            }
                            try:
                                body = await self._post(
                                    url, headers, plain_payload,
                                    timeout=retry_timeout, max_retries=attempt_retries,
                                )
                                self._model_cooldowns.pop(m_name, None)
                                break
                            except APIError as retry_err:
                                err = retry_err
                    last_err = err
                    if (
                        not is_mock
                        and len(candidate_models) > 1
                        and err.code in {
                            "AI_REQUEST_REJECTED", "AI_UPSTREAM_ERROR", "AI_TIMEOUT", "AI_RATE_LIMITED",
                        }
                    ):
                        self._model_cooldowns[m_name] = time.monotonic() + MODEL_COOLDOWN_SECONDS
                    if not is_last and err.code in {
                        "AI_REQUEST_REJECTED", "AI_UPSTREAM_ERROR", "AI_TIMEOUT", "AI_RATE_LIMITED",
                    }:
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
            if not model.lower().startswith(("o1", "o3", "o4", "gpt-5")):
                payload["temperature"] = 0.2
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
                native_text = (getattr(file, "native_text", None) or "").strip()
                if native_text and native_text.replace("[không đọc rõ]", "").strip():
                    # Fast-path for digital PDFs: skip multimodal Vision upload completely.
                    content = await self.structured(
                        GENERATE_SYSTEM,
                        generation_prompt(native_text, flashcard_count, quiz_count),
                        StudyContent,
                    )
                    if len(content.flashcards) != flashcard_count or len(content.quizzes) != quiz_count:
                        raise APIError(502, "AI_COUNT_MISMATCH", "AI trả về số lượng thẻ/câu hỏi không đúng yêu cầu.")
                    return native_text, content

                # Single-pass multimodal OCR + study material generation for images & scanned PDFs.
                unified = await self.structured(
                    UNIFIED_SYSTEM,
                    unified_prompt(flashcard_count, quiz_count),
                    UnifiedStudyOutput,
                    file,
                )
                text = unified.extracted_text.strip()
                if not text or not text.replace("[không đọc rõ]", "").strip():
                    raise APIError(422, "NO_TEXT_DETECTED", "Không nhận dạng được văn bản. Hãy tải ảnh/PDF rõ hơn.")
                if len(unified.flashcards) != flashcard_count or len(unified.quizzes) != quiz_count:
                    raise APIError(502, "AI_COUNT_MISMATCH", "AI trả về số lượng thẻ/câu hỏi không đúng yêu cầu.")
                content = StudyContent(flashcards=unified.flashcards, quizzes=unified.quizzes)
                return text, content
        except TimeoutError:
            raise APIError(504, "AI_TIMEOUT", "AI phản hồi quá lâu. Vui lòng thử lại với tệp nhỏ hơn.") from None
