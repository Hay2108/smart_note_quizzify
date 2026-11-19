# Smart Note & Quizzify Backend Upload và kết nối AI

Bộ mã nguồn cho nhiệm vụ **[BE/AI] Lập trình FastAPI Endpoint Upload & Connection API Module**.
Endpoint `POST /api/v1/upload` nhận ảnh/PDF từ Frontend, gọi Gemini hoặc OpenAI để OCR,
tạo flashcard và quiz, kiểm tra dữ liệu rồi lưu vào SQLite đã được nhóm khởi tạo.

Đã kiểm thử trên Python 3.12. Không có API key thật trong bộ bàn giao.

## 1. Những gì đã triển khai

- Nhận một tệp JPG/JPEG/PNG/WEBP/PDF qua `multipart/form-data`.
- Kiểm tra dung lượng, phần mở rộng, MIME và nội dung tệp thực tế trước khi gọi AI.
- Chuẩn hóa hướng ảnh theo EXIF; bỏ metadata khi gửi ảnh tới AI.
- PDF được kiểm tra bằng pypdf, bao gồm PDF scan; PDF gốc được gửi trực tiếp tới AI có khả năng nhìn ảnh.
- Hai lời gọi AI: **OCR → văn bản thô → tạo JSON flashcard/quiz**. Dùng HTTP bất đồng bộ và structured output.
- Dùng Pydantic kiểm tra JSON, số lượng thẻ, đúng 4 lựa chọn khác nhau và đáp án thuộc danh sách lựa chọn.
- Lưu `documents`, `flashcards`, `quizzes` trong **một transaction**. Có lỗi thì rollback toàn bộ.
- Trả UUID của tài liệu, từng thẻ và từng câu hỏi sau khi commit thành công.
- Tài liệu API tương tác `/docs`, OpenAPI `/openapi.json`, bản xuất `swagger.json`.
- Cấu hình CORS cho Streamlit trên localhost cổng 8501.
- Kiểm thử HTTP adapter và SQLite thật bằng dịch vụ AI giả lập trong test. Ứng dụng không có chế độ tạo dữ liệu giả.

**Tên bảng:** hình ERD sử dụng nhãn DOCUMENTS, FLASH_CARD, QUIZZES nhưng file `database.py`/SQLite
nhóm cung cấp thực tế dùng `documents`, `flashcards`, `quizzes`. Bản này giữ nguyên tên bảng và cột thực tế,
không tạo một bộ bảng khác. `users` và `user_progress` cũng được giữ nguyên.
File `smart_note.db` trong gói là bản sao cơ sở dữ liệu nhóm gửi, với 5 bảng và chưa có bản ghi.

## 2. Cài đặt trên Windows

Giải nén, mở Terminal trong thư mục `smart_note_backend` có `README.md` và `requirements.txt`.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Mở `.env` bằng trình soạn thảo rồi điền API key **của một nhà cung cấp**. Không gửi key trong Frontend,
không đưa `.env` lên Git và không gửi key trong ảnh báo cáo.

Dùng Gemini:

```dotenv
AI_PROVIDER=gemini
GEMINI_API_KEY=DIEN_KEY_CUA_BAN
GEMINI_MODEL=gemini-3.6-flash
```

Hoặc dùng OpenAI:

```dotenv
AI_PROVIDER=openai
OPENAI_API_KEY=DIEN_KEY_CUA_BAN
OPENAI_MODEL=gpt-4.1
```

Các tên model trên khớp với cấu hình mặc định trong `app/config.py` (`gemini-3.6-flash` / `gpt-4.1`). Cần dùng model có trong tài khoản,
hỗ trợ ảnh/PDF và structured output. Quyền truy cập, hạn mức và chi phí do nhà cung cấp quyết định.
Nếu model không được tài khoản hỗ trợ, đổi tên model trong `.env`. Không tự động chuyển nhà cung cấp khi lỗi.

Khởi tạo cơ sở dữ liệu SQLite (tạo 5 bảng `users`, `documents`, `flashcards`, `quizzes`, `user_progress` trong `smart_note.db`):

```powershell
.\.venv\Scripts\python.exe database.py
```

Xác nhận Terminal in ra dòng: `Khởi tạo SQLite thành công với 5 bảng.`

Khởi chạy server FastAPI (hoặc dùng nhanh file `..\run_backend.bat` ở thư mục gốc):

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Mở trên cùng máy chạy backend:

- Swagger UI: <http://127.0.0.1:8000/docs>
- OpenAPI JSON: <http://127.0.0.1:8000/openapi.json>
- Health: <http://127.0.0.1:8000/health>

Đây là địa chỉ cục bộ sau khi bạn khởi động máy chủ, không phải URL đã triển khai công khai.
`/health` chỉ kiểm tra ứng dụng, SQLite và trạng thái có key/model; không gọi AI để xác thực key.

Trên macOS/Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
# Điền key/model vào .env trước khi upload.
.venv/bin/python database.py
.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## 3. Tích hợp SQLite đã có

Mặc định ứng dụng đọc `smart_note.db` **cạnh README.md**, độc lập với thư mục làm việc hiện tại.
Nếu dùng DB của nhóm tại vị trí khác, đặt đường dẫn tuyệt đối trong `.env`, ví dụ:

```dotenv
DATABASE_URL=sqlite:///C:/Projects/SmartNote/smart_note.db
```

Đảm bảo thư mục chứa DB tồn tại và có quyền ghi. Khi startup, `Base.metadata.create_all()` chỉ thêm bảng còn thiếu,
không xóa dữ liệu và không sửa cấu trúc cột đang có. Nếu schema nhóm thay đổi sau này, cần migration riêng.
Mỗi kết nối bật `PRAGMA foreign_keys=ON` và chờ khóa SQLite tối đa 15 giây.

Nếu không truyền `user_id`, backend dùng hồ sơ cục bộ có UUID cố định
`00000000-0000-4000-8000-000000000001`, tự tạo trong transaction lưu tài liệu.
Nếu truyền `user_id`, UUID phải đã có trong `users`; nếu chưa có thì trả 404 trước khi gọi AI.
Ứng dụng không cung cấp đăng nhập hoặc API tạo tài khoản trong phạm vi nhiệm vụ này.

| Bảng | Dữ liệu lưu từ endpoint |
| --- | --- |
| `users` | Tự tạo hồ sơ cục bộ khi cần; không tạo người dùng từ UUID tùy ý |
| `documents` | `doc_id`, `user_id`, tên tệp, văn bản OCR, thời điểm UTC |
| `flashcards` | `card_id`, `doc_id`, câu hỏi, đáp án, thời điểm UTC |
| `quizzes` | `quiz_id`, `doc_id`, câu hỏi, mảng `options` dạng JSON, đáp án, thời điểm UTC |
| `user_progress` | Giữ nguyên; upload chưa tạo kết quả làm bài |

## 4. Hợp đồng với Frontend

> **Tích hợp sẵn:** Ứng dụng Frontend Streamlit tại [`../app.py`](../app.py) ở thư mục gốc đã được tích hợp trực tiếp với endpoint `POST /api/v1/upload` (và kiểm tra trạng thái qua `GET /health`), đồng thời đọc lại dữ liệu từ `smart_note.db`. Xem hướng dẫn chạy toàn bộ hệ thống tại [`../README.md`](../README.md) hoặc khởi chạy nhanh bằng `..\run_frontend.bat`.

### Request

`POST /api/v1/upload`, Content-Type `multipart/form-data`.

| Trường | Kiểu | Bắt buộc | Ý nghĩa |
| --- | --- | --- | --- |
| `file` | File | Có | Một ảnh hoặc PDF |
| `user_id` | Chuỗi UUID | Không | Bỏ hẳn trường để dùng hồ sơ cục bộ |
| `flashcard_count` | Số nguyên 1–20 | Không | Mặc định 5 |
| `quiz_count` | Số nguyên 1–20 | Không | Mặc định 5 |

Không gửi JSON body thay cho multipart. Không đặt Content-Type thủ công trong JavaScript khi dùng FormData;
trình duyệt phải tự tạo multipart boundary.

Ví dụ curl trên Windows với file PDF mẫu `sample_bai_giang_ai.pdf` đi kèm sẵn:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/upload -F "file=@sample_bai_giang_ai.pdf" -F "flashcard_count=5" -F "quiz_count=5"
```

Ví dụ JavaScript:

```javascript
const form = new FormData();
form.append("file", fileInput.files[0]);
form.append("flashcard_count", "5");
form.append("quiz_count", "5");
const response = await fetch("http://127.0.0.1:8000/api/v1/upload", {
  method: "POST",
  body: form,
});
const result = await response.json();
if (!response.ok) throw new Error(result.error.message);
console.log(result.data.doc_id, result.data.flashcards, result.data.quizzes);
```

Ví dụ Streamlit:

```python
import httpx
import streamlit as st

uploaded = st.file_uploader("Chọn ảnh hoặc PDF", type=["jpg", "jpeg", "png", "webp", "pdf"])
if st.button("Tạo học liệu", disabled=uploaded is None):
    # Giữ uploaded trong phiên khi lỗi; không tự lặp upload nhiều lần.
    try:
        with st.spinner("Đang đọc tài liệu và tạo học liệu…"):
            response = httpx.post(
                "http://127.0.0.1:8000/api/v1/upload",
                files={"file": (uploaded.name, uploaded.getvalue(), uploaded.type)},
                data={"flashcard_count": "5", "quiz_count": "5"},
                timeout=150,
            )
        result = response.json()
        if response.is_success:
            st.session_state["study_material"] = result["data"]
            st.success("Đã tạo và lưu học liệu")
            st.json(result["data"])
        else:
            st.error(result["error"]["message"])
    except httpx.RequestError:
        st.error("Chưa kết nối được backend hoặc đã hết thời gian chờ.")
```

### Response thành công — HTTP 201

Ví dụ minh họa với yêu cầu 1 thẻ và 1 câu hỏi (UUID thực tế được sinh mới):

```json
{
  "status": "success",
  "data": {
    "doc_id": "ea930996-0d24-4cbf-8bf7-9a11ea8d60a9",
    "user_id": "00000000-0000-4000-8000-000000000001",
    "file_name": "bai_giang.pdf",
    "extracted_text": "AI là Artificial Intelligence, nghĩa là trí tuệ nhân tạo.",
    "flashcards": [
      {
        "card_id": "e72b4329-7989-48bf-9f21-22c584f8b6e4",
        "front_text": "AI là gì?",
        "back_text": "Trí tuệ nhân tạo"
      }
    ],
    "quizzes": [
      {
        "quiz_id": "33eb7a21-e388-4b02-ad73-cde539f33821",
        "question": "AI là viết tắt của từ nào?",
        "options": ["Artificial Intelligence", "Machine Tool", "Network", "Database"],
        "correct_answer": "Artificial Intelligence"
      }
    ]
  }
}
```

`flashcards` và `quizzes` là **mảng JSON**, không phải chuỗi JSON lồng thêm một lần nữa.
Phản hồi HTTP được FastAPI serialize thành JSON; Frontend gọi `response.json()` một lần.
`correct_answer` là nội dung đáp án, không phải chỉ số hay ký tự A/B/C/D. Bản MVP gửi đáp án cho client để ôn tập,
chưa phù hợp cho một kỳ thi cần giấu đáp án.

### Response lỗi thống nhất

```json
{
  "status": "error",
  "error": {
    "code": "NO_TEXT_DETECTED",
    "message": "Không nhận dạng được văn bản. Hãy tải ảnh/PDF rõ hơn."
  }
}
```

| HTTP | Ví dụ `error.code` | Ý nghĩa |
| --- | --- | --- |
| 400 | `EMPTY_FILE`, `INVALID_IMAGE`, `INVALID_PDF`, `ENCRYPTED_PDF`, `INVALID_FILENAME` | Tệp rỗng, hỏng, giả định dạng hoặc có mật khẩu |
| 404 | `USER_NOT_FOUND` | UUID người dùng chưa tồn tại |
| 413 | `FILE_TOO_LARGE`, `REQUEST_TOO_LARGE`, `IMAGE_TOO_LARGE`, `NORMALIZED_IMAGE_TOO_LARGE` | Vượt giới hạn tệp, request hoặc độ phân giải |
| 415 | `UNSUPPORTED_FILE_TYPE`, `CONTENT_TYPE_MISMATCH`, `ANIMATED_IMAGE` | Định dạng không hỗ trợ |
| 422 | `INVALID_REQUEST`, `PDF_TOO_MANY_PAGES`, `NO_TEXT_DETECTED` | Tham số sai hoặc không có nội dung dùng được |
| 500 | `DATABASE_ERROR` | Không lưu được; transaction đã rollback |
| 502 | `AI_CONNECTION_ERROR`, `AI_REQUEST_REJECTED`, `AI_UPSTREAM_ERROR`, `AI_INVALID_RESPONSE`, `AI_INVALID_JSON`, `AI_INCOMPLETE_RESPONSE`, `AI_COUNT_MISMATCH` | Lỗi nhà cung cấp hoặc dữ liệu AI không hợp lệ |
| 503 | `AI_NOT_CONFIGURED`, `INVALID_MODEL_CONFIG`, `AI_AUTH_ERROR`, `AI_RATE_LIMITED` | Cấu hình/key/model chưa hợp lệ hoặc hết hạn mức |
| 504 | `AI_TIMEOUT` | Quá hạn xử lý AI |

Thông báo từ nhà cung cấp và nội dung lỗi SQL không được chuyển nguyên văn về Frontend.

## 5. Cấu hình và giới hạn

| Biến môi trường | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `AI_PROVIDER` | `gemini` | `gemini` hoặc `openai` |
| `GEMINI_API_KEY`, `OPENAI_API_KEY` | Rỗng | Key của nhà cung cấp được chọn |
| `GEMINI_MODEL`, `OPENAI_MODEL` | `gemini-3.6-flash` / `gpt-4.1` (`from_env()`) | Tên mô hình AI sử dụng; `.env.example` có cấu hình mẫu |
| `DATABASE_URL` | DB cạnh README | Kết nối SQLite |
| `MAX_UPLOAD_MB` | 10 | Giới hạn tệp tính theo MiB = 1024² byte, cấu hình 1–10 |
| `MAX_PDF_PAGES` | 20 | Số trang PDF tối đa, cấu hình 1–100 |
| `AI_TIMEOUT_SECONDS` | 120 | Deadline cho toàn bộ hai bước AI, tối đa 600 |
| `AI_MAX_RETRIES` | 1 | Số lần thử lại khi AI trả HTTP 429/5xx, tối đa 3 |
| `CORS_ORIGINS` | Hai origin Streamlit cục bộ | Danh sách cách nhau bằng dấu phẩy |

Ảnh bị giới hạn 20 triệu điểm ảnh. HTTP request được giới hạn bằng giới hạn tệp cộng 1 MiB cho multipart.
Giới hạn kiểm tra dựa trên số byte nhận thực tế, kể cả upload không có Content-Length.
Dung lượng ảnh sau chuẩn hóa cũng được kiểm tra. PDF chỉ giới hạn byte/trang, không thực thi script hoặc attachment.
Không lưu tệp gốc vào ổ đĩa của ứng dụng; tệp tạm multipart do framework quản lý và được đóng sau khi đọc.
Nội dung được gửi đến nhà cung cấp AI đã chọn, nên việc dùng SQLite cục bộ không có nghĩa là dữ liệu không ra ngoài máy.

Hai bước OCR và tạo học liệu có thể mất nhiều giây. Đây là API trả kết quả đồng bộ, dù phần HTTP tới AI dùng async.
Không khẳng định đáp ứng yêu cầu dưới 3 giây; nếu cần phản hồi nhanh, nhóm nên tách job trả 202 và endpoint tra trạng thái.
Không retry timeout, JSON sai hoặc lỗi HTTP 4xx khác, tránh tự động lặp chi phí không cần thiết.
Nếu chính client timeout sau khi backend đã commit, hãy kiểm tra DB trước khi upload lại.
Chưa có idempotency key, nên hai lần upload thành công cùng tệp sẽ tạo hai tài liệu.

**Giới hạn phạm vi:** endpoint này tự động OCR rồi sinh học liệu theo nhiệm vụ BE/AI hiện tại.
Chưa tách endpoint OCR và endpoint sinh từ văn bản đã sửa để thực hiện đầy đủ bước kiểm duyệt trong UX Specs.
Chưa thêm âm thanh, tóm tắt, môn học, giải thích đáp án, chấm điểm, đăng nhập hoặc API đọc thư viện.
Những trường chưa có trong schema gốc không được ghi vào cột không liên quan.
OCR/AI có thể sai kiến thức dù JSON hợp lệ; cần người dùng kiểm tra học liệu.
Ứng dụng dành cho MVP chạy cục bộ: `user_id` là tham chiếu dữ liệu, không phải xác thực hay phân quyền.

## 6. Swagger và kiểm thử

`swagger.json` có sẵn trong thư mục gốc, định dạng OpenAPI 3.1 do chính FastAPI sinh.
Đội Frontend có thể import tệp này vào công cụ đọc OpenAPI hoặc mở `/docs` sau khi chạy server.
Nếu sửa request/response thì xuất lại:

```powershell
.\.venv\Scripts\python.exe scripts/export_openapi.py
```

Chạy kiểm thử tự động, không cần key và không gọi dịch vụ AI thật:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Test dùng `httpx.MockTransport` giả lập HTTP của Gemini/OpenAI và lưu vào SQLite tạm thực tế.
Bao phủ cả request/response của hai adapter, ảnh/PDF hợp lệ, UUID/link bản ghi, đọc lại qua kết nối độc lập,
tương thích DB nhóm cung cấp, tệp sai định dạng, giới hạn, lỗi AI, JSON/đáp án sai, rollback và Swagger/CORS.
Kết quả chi tiết trong `TEST_RESULTS.txt`. Không dùng test mô phỏng làm bằng chứng OCR chính xác trên ảnh thật.

Chạy thử AI thật **sau khi cấu hình key/model trong `.env` và khởi động server**, sử dụng file PDF mẫu `sample_bai_giang_ai.pdf` có sẵn ngay trong thư mục `smart_note_backend` (và thư mục gốc):

```powershell
.\.venv\Scripts\python.exe scripts/test_upload_api.py sample_bai_giang_ai.pdf --flashcards 5 --quizzes 5
```

Lệnh này gửi dữ liệu tới nhà cung cấp và có thể phát sinh phí. Kiểm tra HTTP 201, nội dung OCR/thẻ/câu hỏi
và bản ghi trong SQLite. Gói bàn giao chưa có kết quả live test vì chưa có API key của nhóm.

Để nghiệm thu trên dữ liệu thật, nên chạy ít nhất một ảnh bài giảng rõ, một PDF có text, một PDF scan,
một ảnh không có chữ và một trường hợp key/hạn mức lỗi. Ghi lại mã HTTP, UUID và kiểm tra nội dung với tài liệu gốc.

## 7. Cấu trúc mã nguồn

| Tệp | Vai trò |
| --- | --- |
| `app/main.py` | FastAPI, endpoint upload, xử lý lỗi, CORS, giới hạn body |
| `app/ai.py` | Kết nối Gemini/OpenAI, parse structured output, deadline và retry |
| `app/prompts.py` | Prompt OCR và tạo học liệu, tách dữ liệu tài liệu khỏi chỉ dẫn |
| `app/files.py` | Đọc upload, kiểm tra ảnh/PDF, chuẩn hóa ảnh |
| `app/database.py` | Định nghĩa 5 bảng SQLAlchemy và kết nối SQLite |
| `app/repository.py` | Hàm lưu dữ liệu AI trong transaction |
| `app/schemas.py` | Schema AI và response Frontend |
| `app/config.py` | Cấu hình từ `.env` |
| `database.py` | Lệnh khởi tạo DB tạo 5 bảng SQLite (`Khởi tạo SQLite thành công với 5 bảng.`) |
| `sample_bai_giang_ai.pdf` | File PDF bài giảng AI mẫu dùng để test nhanh `POST /api/v1/upload` & `scripts/test_upload_api.py` |
| `scripts/export_openapi.py` | Xuất `swagger.json` |
| `scripts/test_upload_api.py` | Upload thử file mẫu (như `sample_bai_giang_ai.pdf`) vào server thật |
| `tests/test_upload.py` | Kiểm thử tích hợp độc lập với mạng AI |
| `../app.py` | Ứng dụng Frontend Streamlit tích hợp trực tiếp với `POST /api/v1/upload` |

## 8. Tài liệu API chính thức đã đối chiếu

- Gemini Generate Content structured outputs: <https://ai.google.dev/gemini-api/docs/generate-content/structured-output>
- Gemini REST request/config: <https://ai.google.dev/api/generate-content>
- Gemini PDF input: <https://ai.google.dev/gemini-api/docs/document-processing>
- OpenAI Responses structured outputs: <https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses>
- OpenAI file inputs: <https://developers.openai.com/api/docs/guides/file-inputs>

Adapter Gemini dùng `generateContent` với `generationConfig.responseFormat.text` theo REST reference.
Adapter OpenAI dùng `/v1/responses`, `input_image`/`input_file`, và `text.format` có JSON Schema strict.
Không cần cài SDK riêng cho mỗi nhà cung cấp vì dự án gọi REST bằng `httpx`.
