# Smart Note & Quizzify — Trợ lý Học tập Tốc độ

**Smart Note & Quizzify** là ứng dụng hỗ trợ học tập giúp sinh viên và giảng viên biến tài liệu bài giảng (ảnh chụp bảng đen, slide bài giảng, tệp PDF) thành **văn bản chuẩn hóa (OCR)**, **bản tóm tắt trọng tâm**, **bộ thẻ ghi nhớ (Flashcard)** và **bộ câu hỏi trắc nghiệm (Quiz)** nhờ AI, đồng thời lưu trữ bền vững trên cơ sở dữ liệu **SQLite** cục bộ.

---

## 1. Tổng quan kiến trúc

Hệ thống gồm 2 thành phần chạy song song trên máy cục bộ:

1. **Backend (`smart_note_backend/`) — FastAPI + SQLite + Gemini / OpenAI**
   - Cung cấp endpoint `POST /api/v1/upload` (`multipart/form-data`), kiểm tra tính hợp lệ của tệp ảnh (`JPG`, `JPEG`, `PNG`, `WEBP`) và `PDF`, chuẩn hóa hướng ảnh EXIF, gọi AI qua REST (`httpx`) với *structured output* để OCR và sinh Flashcard / Quiz, rồi lưu toàn bộ vào **SQLite (`smart_note.db`)** trong một transaction duy nhất.
   - Hỗ trợ tài liệu API tương tác **Swagger UI** (`/docs`), đặc tả OpenAPI (`/openapi.json`, `swagger.json`) và endpoint kiểm tra sức khỏe hệ thống `GET /health`.
2. **Frontend (`app.py`) — Streamlit (Google Material Design, 6 màn hình wireframe)**
   - Kết nối trực tiếp tới Backend (`http://127.0.0.1:8000/api/v1/upload`), đọc lại dữ liệu đã lưu từ `smart_note_backend/smart_note.db`.
   - **6 màn hình theo wireframe:**
     - **Màn 1 — Tải lên:** Chọn file bài giảng, chọn môn học, cấu hình số lượng Flashcard / Quiz (1–20, mặc định 5) ở sidebar và bấm `Bắt đầu xử lý`. *(Backend tiếp nhận ảnh `JPG/JPEG/PNG/WEBP` và `PDF`, mặc định tối đa `10 MiB` và `20` trang PDF; Frontend kiểm tra quy tắc FR14 trước khi gửi).*
     - **Màn 2 — Xem và sửa văn bản:** Xem văn bản trích xuất từ AI, chỉnh sửa trực tiếp các công thức/thuật ngữ nếu cần, bấm `Lưu` hoặc `Sinh nội dung`.
     - **Màn 3 — Kết quả:** Xem bộ học liệu vừa tạo qua 3 tab **Tóm tắt**, **Flashcard**, **Trắc nghiệm** (kèm đáp án & giải thích).
     - **Màn 4 — Ôn flashcard:** Thẻ lật 3D (`Lật thẻ`), tự đánh giá `Đã nhớ` / `Chưa nhớ`, thống kê tỷ lệ ghi nhớ và chế độ `Ôn lại ... thẻ chưa nhớ`.
     - **Màn 5 — Làm trắc nghiệm:** Làm bài từng câu, bấm `Nộp bài & xem điểm` để chấm điểm tự động và xem đáp án + giải thích chi tiết từng câu.
     - **Màn 6 — Thư viện:** Hiển thị các bộ học liệu lưu trong `smart_note.db`, hỗ trợ tìm kiếm theo từ khóa, lọc theo môn học và bấm `Mở` để nạp thẳng vào Màn 3.

---

## 2. Cấu trúc thư mục dự án

```text
smart_note_quizzify_fe/
├── app.py                          # Giao diện Frontend Streamlit (Google Material Design, 6 màn hình)
├── requirements.txt                # Danh sách thư viện đầy đủ (kế thừa smart_note_backend/requirements.txt + Streamlit)
├── run_backend.bat                 # File chạy nhanh Backend FastAPI trên Windows (cổng 8000)
├── run_frontend.bat                # File chạy nhanh Frontend Streamlit trên Windows (cổng 8501)
├── sample_bai_giang_ai.pdf         # File PDF bài giảng AI mẫu (2 trang) dùng để kiểm thử nhanh
├── test_integration_and_logic.py   # Bộ kiểm thử logic Frontend & tích hợp API (5/5 test)
├── README.md                       # Tài liệu hướng dẫn cài đặt & sử dụng (tệp hiện tại)
├── .streamlit/
│   └── config.toml                 # Giao diện sáng Material Design & cấu hình Streamlit
└── smart_note_backend/
    ├── database.py                 # Script khởi tạo 5 bảng SQLite trong smart_note.db
    ├── requirements.txt            # Thư viện riêng cho Backend FastAPI
    ├── .env.example                # Mẫu cấu hình biến môi trường (copy thành .env trước khi chạy)
    ├── smart_note.db               # Cơ sở dữ liệu SQLite (users, documents, flashcards, quizzes, user_progress)
    ├── sample_bai_giang_ai.pdf     # Bản sao PDF mẫu phục vụ test Backend CLI/API
    ├── swagger.json                # Đặc tả OpenAPI 3.1 xuất sẵn từ FastAPI
    ├── pytest.ini                  # Cấu hình pytest cho Backend
    ├── README.md                   # Tài liệu kỹ thuật chi tiết của Backend
    ├── app/
    │   ├── main.py                 # Ứng dụng FastAPI, CORS, giới hạn upload, /health, /api/v1/upload
    │   ├── config.py               # Đọc biến môi trường từ smart_note_backend/.env
    │   ├── ai.py                   # Adapter kết nối Gemini / OpenAI REST API
    │   ├── files.py                # Kiểm tra tệp ảnh/PDF, số trang và chuẩn hóa EXIF
    │   ├── database.py             # Định nghĩa 5 bảng SQLAlchemy & cấu hình SQLite
    │   ├── repository.py           # Lưu dữ liệu AI theo transaction (rollback khi lỗi)
    │   ├── schemas.py              # Pydantic schema kiểm tra JSON đầu ra
    │   ├── prompts.py              # Prompt OCR và sinh Flashcard/Quiz
    │   └── errors.py               # Chuẩn mã lỗi APIError & ErrorResponse JSON
    ├── scripts/
    │   ├── test_upload_api.py      # Script CLI gửi file thật tới POST /api/v1/upload
    │   └── export_openapi.py       # Xuất lại file swagger.json
    └── tests/
        └── test_upload.py          # Bộ kiểm thử tự động Backend (pytest, mock HTTP AI + SQLite thật)
```

---

## 3. Hướng dẫn cài đặt và chạy từng bước

**Yêu cầu tiên quyết:**
- Đã cài **Python 3.10 trở lên** (khuyến nghị Python 3.12+; đã kiểm thử trên Python 3.12 và 3.14).
- Có sẵn **API Key** của **Google Gemini** *(khuyến nghị, mặc định trong cấu hình)* hoặc **OpenAI**, với model hỗ trợ đọc ảnh/PDF và *structured output*.

> **Lưu ý trên Windows:** Thầy/Cô có thể mở **PowerShell** (hoặc Command Prompt) tại thư mục gốc `smart_note_quizzify_fe` để thực hiện các bước bên dưới. Từ Bước 4 trở đi cần mở **2 cửa sổ Terminal song song** (1 cho Backend, 1 cho Frontend) hoặc dùng 2 file `.bat` đi kèm.

---

### Bước 1: Tạo môi trường ảo & cài đặt thư viện (`requirements.txt`)

#### Cách A — Cài đặt trọn bộ Backend + Frontend tại thư mục gốc *(Khuyến nghị)*

File `requirements.txt` ở thư mục gốc đã tự động tham chiếu `-r smart_note_backend/requirements.txt` cùng `streamlit` và `requests`, nên chỉ cần tạo **1 môi trường ảo** tại thư mục gốc.

- **Windows (PowerShell):**
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\python.exe -m pip install --upgrade pip
  .\.venv\Scripts\python.exe -m pip install -r requirements.txt
  ```
- **macOS / Linux:**
  ```bash
  python3 -m venv .venv
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r requirements.txt
  ```

#### Cách B — Chỉ cài đặt riêng cho Backend (`smart_note_backend\requirements.txt`)

Nếu muốn tách riêng môi trường cho Backend hoặc chỉ kiểm thử API:

- **Windows (PowerShell):**
  ```powershell
  cd smart_note_backend
  python -m venv .venv
  .\.venv\Scripts\python.exe -m pip install --upgrade pip
  .\.venv\Scripts\python.exe -m pip install -r requirements.txt
  ```
- **macOS / Linux:**
  ```bash
  cd smart_note_backend
  python3 -m venv .venv
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r requirements.txt
  ```

---

### Bước 2: Cấu hình biến môi trường (`.env`)

1. Sao chép file mẫu `smart_note_backend\.env.example` thành `smart_note_backend\.env`:
   - **Windows (PowerShell, tại thư mục gốc):**
     ```powershell
     Copy-Item smart_note_backend\.env.example smart_note_backend\.env
     ```
   - **macOS / Linux:**
     ```bash
     cp smart_note_backend/.env.example smart_note_backend/.env
     ```

2. Mở tệp `smart_note_backend\.env` bằng trình soạn thảo (Notepad / VS Code) và thay thế giá trị mẫu (`YOUR_GEMINI_API_KEY_HERE` hoặc `YOUR_OPENAI_API_KEY_HERE`) bằng API key thật của **một nhà cung cấp**:

   - **Dùng Google Gemini (mặc định):**
     ```dotenv
     AI_PROVIDER=gemini
     GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
     GEMINI_MODEL=gemini-3.6-flash
     ```
   - **Hoặc dùng OpenAI:**
     ```dotenv
     AI_PROVIDER=openai
     OPENAI_API_KEY=YOUR_OPENAI_API_KEY_HERE
     OPENAI_MODEL=gpt-4.1
     ```

   *(Các biến cấu hình chính trong `smart_note_backend/.env`:)*

   | Biến môi trường | Giá trị mặc định | Ý nghĩa |
   | --- | --- | --- |
   | `AI_PROVIDER` | `gemini` | Nhà cung cấp AI (`gemini` hoặc `openai`) |
   | `GEMINI_API_KEY` | *(điền key của bạn)* | API key Google Gemini (khi dùng `gemini`) |
   | `GEMINI_MODEL` | `gemini-3.6-flash` | Tên model Gemini hỗ trợ ảnh/PDF & structured output |
   | `OPENAI_API_KEY` | *(điền key của bạn)* | API key OpenAI (khi dùng `openai`) |
   | `OPENAI_MODEL` | `gpt-4.1` | Tên model OpenAI hỗ trợ ảnh/PDF & structured output |
   | `DATABASE_URL` | `sqlite:///.../smart_note.db` | Để trống/comment để mặc định dùng `smart_note_backend/smart_note.db` |
   | `MAX_UPLOAD_MB` | `10` | Dung lượng tệp tải lên tối đa (1–10 MiB) |
   | `MAX_PDF_PAGES` | `20` | Số trang PDF tối đa (1–100 trang) |
   | `AI_TIMEOUT_SECONDS` | `120` | Thời gian chờ tối đa cho 2 bước AI (giây, tối đa 600) |
   | `AI_MAX_RETRIES` | `1` | Số lần tự động thử lại khi AI trả HTTP 429/5xx (0–3) |
   | `CORS_ORIGINS` | `http://localhost:8501,http://127.0.0.1:8501` | Các địa chỉ Frontend được phép gọi API |

> **Cảnh báo bảo mật:** Tuyệt đối **không chia sẻ API key thật**, không đưa tệp `smart_note_backend/.env` lên Git (đã được chặn trong `.gitignore`), và không chụp ảnh màn hình lộ API key trong báo cáo. Frontend (`app.py`) không lưu trữ và không gửi API key.

---

### Bước 3: Khởi tạo cơ sở dữ liệu SQLite (`database.py`)

Di chuyển vào thư mục `smart_note_backend` và chạy `database.py` để tạo đủ **5 bảng** (`users`, `documents`, `flashcards`, `quizzes`, `user_progress`) trong tệp `smart_note_backend\smart_note.db`:

- **Windows (PowerShell):**
  ```powershell
  cd smart_note_backend
  ..\.venv\Scripts\python.exe database.py
  ```
  *(Nếu đã kích hoạt `.venv` hoặc cài thư viện vào Python hệ thống, có thể chạy trực tiếp `python database.py`; nếu dùng `.venv` riêng trong `smart_note_backend`, dùng `.\.venv\Scripts\python.exe database.py`.)*

- **macOS / Linux:**
  ```bash
  cd smart_note_backend
  ../.venv/bin/python database.py
  ```

**Xác nhận kết quả thành công trên Terminal:**
```text
Khởi tạo SQLite thành công với 5 bảng.
```

---

### Bước 4: Khởi động Backend FastAPI

- **Cách 1 — Chạy qua Terminal (tại thư mục `smart_note_backend`):**
  - **Windows (PowerShell):**
    ```powershell
    cd smart_note_backend
    ..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
    ```
    *(Hoặc `python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` nếu đã kích hoạt môi trường ảo; thêm `--reload-include "*.env"` nếu muốn server tự nạp lại khi chỉnh sửa `.env`.)*
  - **macOS / Linux:**
    ```bash
    cd smart_note_backend
    ../.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
    ```

- **Cách 2 — Chạy nhanh trên Windows bằng `.bat` shortcut:**
  - Double-click tệp **`run_backend.bat`** ngay tại thư mục gốc `smart_note_quizzify_fe`. Script tự động tìm Python (`.venv` → `PATH` → Python hệ thống), tự chạy `database.py` nếu chưa có `smart_note.db`, nhắc nếu thiếu `.env` và khởi động FastAPI ở cổng `8000` (tạm dừng `pause` để hiển thị rõ nếu có lỗi).

**Kiểm tra Backend đã sẵn sàng:**
- Mở trình duyệt tới **Health Check**: <http://127.0.0.1:8000/health>
  → Kết quả mong đợi: `{"status": "ok", "database": "ok", "ai_provider": "gemini", "ai_configured": true}` *(khi đã cấu hình đúng API key và model trong `.env`)*.
- Mở **Swagger UI** (tài liệu API tương tác): <http://127.0.0.1:8000/docs>.

> Giữ nguyên cửa sổ Terminal/Command Prompt này đang chạy trong suốt quá trình sử dụng ứng dụng.

---

### Bước 5: Khởi động Frontend Streamlit

- **Cách 1 — Chạy qua Terminal:** Mở **cửa sổ Terminal thứ 2** tại thư mục gốc `smart_note_quizzify_fe`:
  - **Windows (PowerShell):**
    ```powershell
    .\.venv\Scripts\python.exe -m streamlit run app.py
    ```
    *(Hoặc `python -m streamlit run app.py` nếu đã kích hoạt môi trường ảo).*
  - **macOS / Linux:**
    ```bash
    .venv/bin/python -m streamlit run app.py
    ```

- **Cách 2 — Chạy nhanh trên Windows bằng `.bat` shortcut:**
  - Double-click tệp **`run_frontend.bat`** ngay tại thư mục gốc `smart_note_quizzify_fe` (script tự động tìm Python `.venv` → `PATH` → Python hệ thống và mở Streamlit).

**Truy cập giao diện web:**
- Trình duyệt sẽ tự mở địa chỉ: **<http://localhost:8501>** (nếu chưa tự mở, hãy copy đường dẫn này vào trình duyệt).
- *(Mẹo kiểm tra kết nối:)* Ở thanh bên trái (Sidebar), mở mục **`Cấu hình Dev / QA Test`** → bấm nút **`Kiểm tra /health`** để xác nhận trạng thái xanh `Backend OK` và `AI Key: Sẵn sàng`. Tại đây bạn cũng có thể chỉnh **Số Flashcard** và **Số Quiz** muốn AI tạo (từ `1` đến `20`, mặc định `5`).

---

### Bước 6: Kiểm thử nhanh với file PDF mẫu (`sample_bai_giang_ai.pdf`)

Trong dự án có sẵn file PDF 2 trang **`sample_bai_giang_ai.pdf`** (*Nhập môn Trí tuệ Nhân tạo & Mạng Nơ-ron Nhân tạo*) ngay ở thư mục gốc (và một bản sao trong `smart_note_backend/`). Thầy/Cô có thể kiểm thử toàn bộ luồng 6 màn hình như sau:

1. **Màn 1 — Tải lên:**
   - Tại trang **Tạo mới**, kéo thả hoặc chọn tệp `sample_bai_giang_ai.pdf`.
   - Chọn môn học **`Trí tuệ nhân tạo (AI)`** và bấm **`Bắt đầu xử lý`**.
   - Frontend sẽ gửi `POST http://127.0.0.1:8000/api/v1/upload` (nhận HTTP `201 Created`).
2. **Màn 2 — Xem và sửa văn bản:**
   - Kiểm tra văn bản tiếng Việt và công thức đã được AI OCR trích xuất từ PDF.
   - Có thể chỉnh sửa trực tiếp trong ô văn bản rồi bấm **`Lưu`**, hoặc bấm **`Sinh nội dung`** để chuyển sang Màn 3.
3. **Màn 3 — Kết quả:**
   - Kiểm tra lần lượt 3 tab: **Tóm tắt**, **Flashcard**, và **Trắc nghiệm** (bấm `Xem đáp án & giải thích` dưới từng câu hỏi).
4. **Màn 4 — Ôn flashcard:**
   - Bấm **`Ôn flashcard`** ở cuối Màn 3.
   - Bấm **`Lật thẻ`** để xem đáp án ở mặt sau, chọn **`Đã nhớ`** hoặc **`Chưa nhớ`** cho từng thẻ.
   - Sau khi hết bộ thẻ, xem vòng tròn tổng kết `% Đã nhớ` và thử nút **`Ôn lại ... thẻ chưa nhớ`** (nếu có).
5. **Màn 5 — Làm trắc nghiệm:**
   - Bấm **`Làm trắc nghiệm`** (từ Màn 3 hoặc Màn 4).
   - Chọn đáp án từng câu rồi bấm **`Câu tiếp`**, đến câu cuối bấm **`Nộp bài & xem điểm`**.
   - Kiểm tra điểm tổng kết, số câu đúng/sai và phần giải thích từng câu.
6. **Màn 6 — Thư viện:**
   - Bấm **`Thư viện`** ở thanh điều hướng bên trái (hoặc **`Về Thư viện`**).
   - Kiểm tra bộ học liệu vừa tạo đã được nạp từ SQLite (`smart_note_backend/smart_note.db`). Nếu cần làm mới từ CSDL, mở **`Cấu hình Dev / QA Test`** và bấm **`Đồng bộ SQLite`**.
   - Thử ô tìm kiếm, bộ lọc môn học và bấm **`Mở`** trên một thẻ để mở lại thẳng vào Màn 3.

---

### Bước 7: Chạy bộ kiểm thử tự động (`pytest` & `test_integration_and_logic.py`)

Hai bộ kiểm thử tự động dưới đây chạy hoàn toàn độc lập với mạng (sử dụng mock HTTP transport / mock `requests.post`), **không cần API key thật và không tốn chi phí AI**:

1. **Kiểm thử Backend (`pytest`):**
   ```powershell
   cd smart_note_backend
   ..\.venv\Scripts\python.exe -m pytest tests -q
   ```
   *(Hoặc `.\.venv\Scripts\python.exe -m pytest -q` / `python -m pytest tests -q`).*
   Kiểm tra cả 2 adapter Gemini/OpenAI, validate ảnh/PDF, giới hạn dung lượng/số trang, transaction SQLite, rollback khi lỗi, Swagger và CORS.

2. **Kiểm thử Frontend & tích hợp API (`test_integration_and_logic.py`):**
   ```powershell
   # Chạy tại thư mục gốc smart_note_quizzify_fe
   .\.venv\Scripts\python.exe test_integration_and_logic.py
   ```
   Kiểm tra tính duy nhất của toàn bộ Streamlit widget keys, xác nhận không còn Mock JSON, logic lật thẻ Flashcard, logic chấm điểm Trắc nghiệm, và contract `POST /api/v1/upload` + Toast/Alert. Kỳ vọng in ra:
   `==> TẤT CẢ BÀI KIỂM THỬ ĐỀU THÀNH CÔNG (5/5 PASSED)!`

3. **Kiểm thử gọi AI thật qua dòng lệnh (tùy chọn, sau khi đã chạy Backend và điền API key vào `.env`):**
   ```powershell
   cd smart_note_backend
   ..\.venv\Scripts\python.exe scripts/test_upload_api.py sample_bai_giang_ai.pdf --flashcards 5 --quizzes 5
   ```

---

## 4. Xử lý lỗi thường gặp (Troubleshooting)

| Triệu chứng / Mã lỗi | Nguyên nhân | Cách khắc phục |
| --- | --- | --- |
| **`BACKEND_UNREACHABLE`** trên Streamlit | Backend FastAPI chưa được khởi động hoặc chạy khác cổng `8000`. | Mở Terminal chạy `run_backend.bat` hoặc `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` trong `smart_note_backend`, rồi bấm **Thử lại**. |
| **`AI_NOT_CONFIGURED` / `AI_AUTH_ERROR`** *(HTTP 503)* | Chưa tạo `smart_note_backend/.env`, chưa điền API key, hoặc API key sai/hết hiệu lực. | Copy `.env.example` thành `.env`, điền đúng `GEMINI_API_KEY` (hoặc `OPENAI_API_KEY`) tương ứng với `AI_PROVIDER`, khởi động lại Backend nếu cần. |
| **`INVALID_MODEL_CONFIG`** *(HTTP 503)* hoặc lỗi model không hỗ trợ | Tên `GEMINI_MODEL` / `OPENAI_MODEL` sai định dạng hoặc tài khoản không có quyền dùng model đó. | Kiểm tra lại tên model trong `smart_note_backend/.env` (mặc định `gemini-3.6-flash` hoặc `gpt-4.1`), đảm bảo model hỗ trợ ảnh/PDF & structured output. |
| **`AI_RATE_LIMITED`** *(HTTP 503)* hoặc **`AI_TIMEOUT`** *(HTTP 504)* | Vượt hạn mức gọi API của nhà cung cấp hoặc AI xử lý quá thời gian `AI_TIMEOUT_SECONDS` (120s). | Đợi vài chục giây rồi bấm **Thử lại**, giảm `flashcard_count`/`quiz_count` xuống hoặc tăng `AI_TIMEOUT_SECONDS` trong `.env`. |
| **`NO_TEXT_DETECTED`** *(HTTP 422)* | Ảnh/PDF mờ, không có chữ đọc được hoặc ảnh trống. | Thử lại với ảnh chụp rõ nét, đủ ánh sáng hoặc file PDF mẫu `sample_bai_giang_ai.pdf`. |
| **`PDF_TOO_MANY_PAGES`** *(HTTP 422)* / **`FILE_TOO_LARGE`** *(HTTP 413)* | Tệp vượt quá giới hạn mặc định Backend (`20` trang PDF hoặc `10 MiB`). | Chia nhỏ PDF hoặc giảm kích thước ảnh trước khi tải lên (hoặc chỉnh `MAX_UPLOAD_MB` / `MAX_PDF_PAGES` trong `.env` theo giới hạn cho phép). |
| **`UNSUPPORTED_FILE_TYPE`** *(HTTP 415)* / lỗi **FR14** | Định dạng tệp không thuộc danh sách hỗ trợ (`JPG`, `JPEG`, `PNG`, `WEBP`, `PDF` ở Backend). | Chỉ tải lên ảnh (`JPG/PNG/WEBP`) hoặc tài liệu `PDF` hợp lệ. |
| **`DATABASE_ERROR`** *(HTTP 500)* hoặc Thư viện trống | Chưa khởi tạo bảng trong `smart_note.db` hoặc tệp DB đang bị khóa bởi tiến trình khác. | Chạy lại `python database.py` trong `smart_note_backend`, đóng các phần mềm đang mở `smart_note.db` rồi bấm **Đồng bộ SQLite**. |
| **`ModuleNotFoundError`** khi chạy Python | Chưa cài `requirements.txt` hoặc chạy nhầm Python ngoài `.venv`. | Cài lại bằng `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` và chạy mọi lệnh bằng Python trong `.venv`. |
| Lỗi cổng `8000` hoặc `8501` đã bị chiếm | Đang có phiên Backend/Streamlit cũ chạy ngầm. | Tắt các cửa sổ Terminal cũ hoặc chạy lại với `--port` khác (ví dụ `--port 8001`, và cập nhật **Backend Base URL** trong sidebar Streamlit). |
