"""
Bộ kiểm thử tự động (Unit & Integration Tests) cho Smart Note & Quizzify:
  1. Kiểm tra tính duy nhất của toàn bộ Streamlit widget/container keys trong `app.py` (AST check).
  2. Kiểm tra việc gỡ bỏ hoàn toàn Mock JSON & dead audio/Speech-to-Text constants.
  3. Kiểm thử đồng bộ giới hạn FR14 Frontend ↔ Backend (10 MB, JPG/JPEG/PNG/WEBP/PDF, reject audio/empty/>10 MB).
  4. Kiểm thử loại bỏ hoàn toàn `time.sleep(...)` giả lập & tái sử dụng HTTP Session.
  5. Kiểm thử logic lật thẻ (flip) & đánh giá thẻ Đã nhớ / Chưa nhớ (Màn 4).
  6. Kiểm thử logic tính điểm Trắc nghiệm & chuẩn hoá đáp án (Màn 5).
  7. Kiểm thử tích hợp trực tiếp `POST /api/v1/upload`, đọc header `X-Process-Time-Ms`,
     phủ toàn bộ mã lỗi Backend trong `render_error_alert_with_hint`, và hệ thống Toast động.

Chạy: python test_integration_and_logic.py
"""

import ast
import collections
import logging
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.getLogger("streamlit").setLevel(logging.ERROR)
logging.getLogger("streamlit.runtime.scriptrunner_utils.script_run_context").setLevel(logging.ERROR)

import app


SAMPLE_BACKEND_STUDY_SET = {
    "doc_id": "2c6a92f6-7b1f-4d33-9b8e-100000000099",
    "user_id": "00000000-0000-4000-8000-000000000001",
    "file_name": "bai_giang_ai.pdf",
    "subject": "Trí tuệ nhân tạo (AI)",
    "extracted_text": (
        "CHƯƠNG 3: MẠNG NƠ-RON NHÂN TẠO (ANN)\n"
        "- Lan truyền tiến (Forward Propagation) tính đầu ra dự đoán.\n"
        "- Lan truyền ngược (Backpropagation) cập nhật trọng số bằng đạo hàm chuỗi.\n"
        "- Hàm kích hoạt ReLU giúp giảm hiện tượng triệt tiêu đạo hàm."
    ),
    "flashcards": [
        {
            "card_id": "fc-uuid-001",
            "front_text": "Forward Propagation trong ANN làm nhiệm vụ gì?",
            "back_text": "Tính toán đầu ra dự đoán đi qua các tầng ẩn từ đầu vào.",
        },
        {
            "card_id": "fc-uuid-002",
            "front_text": "Backpropagation dùng quy tắc toán học nào?",
            "back_text": "Quy tắc đạo hàm hàm hợp (Chain Rule) để tính gradient theo trọng số.",
        },
        {
            "card_id": "fc-uuid-003",
            "front_text": "Ưu điểm chính của hàm kích hoạt ReLU là gì?",
            "back_text": "Giảm thiểu hiện tượng triệt tiêu đạo hàm (Vanishing Gradient) và tăng tốc hội tụ.",
        },
    ],
    "quizzes": [
        {
            "quiz_id": "qz-uuid-001",
            "question": "Thuật toán nào dùng Chain Rule để truyền ngược sai số và cập nhật trọng số mạng nơ-ron?",
            "options": [
                "Backpropagation",
                "K-Means Clustering",
                "Min-Max Normalization",
                "Breadth-First Search",
            ],
            "correct_answer": "Backpropagation",
        },
        {
            "quiz_id": "qz-uuid-002",
            "question": "Quá trình tính toán tín hiệu từ tầng đầu vào qua các tầng ẩn tới tầng đầu ra gọi là gì?",
            "options": [
                "A. Dropout Regularization",
                "B. Forward Propagation",
                "C. Batch Normalization",
                "D. Gradient Clipping",
            ],
            "correct_answer": "B. Forward Propagation",
        },
        {
            "quiz_id": "qz-uuid-003",
            "question": "Hàm kích hoạt ReLU có công thức toán học nào sau đây?",
            "options": [
                "A. f(x) = 1 / (1 + e^-x)",
                "B. f(x) = max(0, x)",
                "C. f(x) = tanh(x)",
                "D. f(x) = x^2",
            ],
            "correct_answer": "B. f(x) = max(0, x)",
        },
        {
            "quiz_id": "qz-uuid-004",
            "question": "Hiện tượng đạo hàm tiến dần về 0 khi mạng quá sâu được gọi là gì?",
            "options": [
                "Vanishing Gradient",
                "Exploding Gradient",
                "Overfitting",
                "Underfitting",
            ],
            "correct_answer": "Vanishing Gradient",
        },
    ],
}


def test_unique_streamlit_keys() -> None:
    """Đảm bảo mọi widget/container key trong app.py là duy nhất."""
    src = Path("app.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    keys = collections.defaultdict(list)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg == "key" and isinstance(kw.value, ast.Constant):
                    keys[kw.value.value].append(node.lineno)
    duplicates = {k: lines for k, lines in keys.items() if len(lines) > 1}
    assert not duplicates, f"Phát hiện trùng lặp key: {duplicates}"


def test_mock_json_completely_removed() -> None:
    """Đảm bảo file mock_data.json, các hàm Mock JSON và nhánh audio chết đã được gỡ bỏ hoàn toàn."""
    assert not Path("mock_data.json").exists(), "File mock_data.json vẫn còn tồn tại!"
    assert not hasattr(app, "load_mock_json"), "Hàm load_mock_json vẫn còn trong app.py!"
    assert not hasattr(app, "mock_api_upload"), "Hàm mock_api_upload vẫn còn trong app.py!"
    assert not hasattr(app, "API_MODE_MOCK"), "Hằng số API_MODE_MOCK vẫn còn trong app.py!"
    assert not hasattr(app, "AUDIO_EXTENSIONS"), "Hằng số AUDIO_EXTENSIONS không được Backend hỗ trợ vẫn còn!"
    assert not hasattr(app, "BACKEND_NATIVE_EXTENSIONS"), "Hằng số thừa BACKEND_NATIVE_EXTENSIONS vẫn còn!"


def test_fr14_upload_validation_aligned_with_backend() -> None:
    """Kiểm thử giới hạn FR14 khớp tuyệt đối Backend: 10 MB và chỉ JPG, JPEG, PNG, WEBP, PDF."""
    assert app.MAX_FILE_SIZE_MB == 10
    assert app.ALLOWED_EXTENSIONS == {"jpg", "jpeg", "png", "webp", "pdf"}

    ten_mb = 10 * 1024 * 1024
    # Hợp lệ: đủ 5 định dạng và dung lượng <= 10 MB
    for name in ("bang_den.jpg", "SLIDE.JPEG", "ghi_chu.png", "hinh_anh.webp", "bai_giang.pdf"):
        ok, err = app.validate_upload(SimpleNamespace(name=name, size=ten_mb))
        assert ok is True and err == "", f"File hợp lệ {name} bị từ chối: {err}"

    # Không hợp lệ: file âm thanh hoặc định dạng ngoài danh sách Backend
    for bad_name in ("ghi_am.mp3", "bai_giang.wav", "audio.m4a", "malware.exe", "notes.docx", "no_ext"):
        ok, err = app.validate_upload(SimpleNamespace(name=bad_name, size=1024))
        assert ok is False and "FR14" in err, f"File không hỗ trợ {bad_name} phải bị chặn!"

    # Không hợp lệ: file rỗng 0 byte
    ok_empty, err_empty = app.validate_upload(SimpleNamespace(name="empty.png", size=0))
    assert ok_empty is False and "FR14" in err_empty

    # Không hợp lệ: vượt quá 10 MB
    ok_big, err_big = app.validate_upload(SimpleNamespace(name="big_slide.pdf", size=ten_mb + 1))
    assert ok_big is False and "FR14" in err_big and "10 MB" in err_big

    # Kiểm tra chuẩn hoá MIME type khớp smart_note_backend/app/files.py
    assert app.canonical_mime_type("a.jpg") == "image/jpeg"
    assert app.canonical_mime_type("a.jpeg") == "image/jpeg"
    assert app.canonical_mime_type("a.png") == "image/png"
    assert app.canonical_mime_type("a.webp") == "image/webp"
    assert app.canonical_mime_type("a.pdf") == "application/pdf"


def test_zero_fake_sleep_and_http_session_reuse() -> None:
    """Đảm bảo không còn time.sleep giả lập trong app.py và HTTP Session được tái sử dụng."""
    src = Path("app.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    sleep_lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "sleep":
                sleep_lines.append(node.lineno)
            elif isinstance(func, ast.Name) and func.id == "sleep":
                sleep_lines.append(node.lineno)
    assert not sleep_lines, f"Phát hiện lời gọi sleep giả lập tại dòng: {sleep_lines}"

    # simulate_error=True phải trả về tức thì (không sleep)
    t0 = time.perf_counter()
    sim_res = app.api_upload(
        file_info={"name": "test.png", "bytes": b"PNG", "type": "image/png"},
        subject="Trí tuệ nhân tạo (AI)",
        simulate_error=True,
    )
    assert sim_res["status"] == "error"
    assert (time.perf_counter() - t0) < 0.1

    # api_finalize_study_set phải hoàn tất tức thì (không sleep)
    study_set = app.normalize_study_set(SAMPLE_BACKEND_STUDY_SET)
    app.st.session_state.pending_study_set = study_set
    app.st.session_state.extracted_text = study_set["extracted_text"]
    t1 = time.perf_counter()
    fin_res = app.api_finalize_study_set(
        raw_text=study_set["extracted_text"],
        subject="Trí tuệ nhân tạo (AI)",
        file_name="bai_giang_ai.pdf",
        simulate_error=False,
    )
    assert fin_res["status"] == "success"
    assert (time.perf_counter() - t1) < 0.1

    # Session HTTP tái sử dụng qua @st.cache_resource
    session_1 = app.get_http_session()
    session_2 = app.get_http_session()
    assert isinstance(session_1, requests.Session)
    assert session_1 is session_2


def test_flashcard_flip_and_review_logic() -> None:
    """Kiểm thử logic lật thẻ 3D và ghi nhận Đã nhớ / Chưa nhớ."""
    study_set = app.normalize_study_set(SAMPLE_BACKEND_STUDY_SET)
    app.st.session_state.current_study_set = study_set

    app.start_flashcards()
    assert app.st.session_state.fc_pos == 0
    assert app.st.session_state.fc_flipped is False
    assert app.st.session_state.fc_known == []
    assert app.st.session_state.fc_unknown == []

    # Lật sang mặt sau rồi lật lại mặt trước
    assert app.flip_flashcard_state() is True
    assert app.st.session_state.fc_flipped is True
    assert app.st.session_state.fc_anim == "flip"
    assert app.flip_flashcard_state() is False

    # Đánh giá thẻ 0: Đã nhớ, thẻ 1: Chưa nhớ
    app.record_flashcard_review(0, is_known=True)
    assert app.st.session_state.fc_pos == 1
    assert app.st.session_state.fc_known == [0]
    assert app.st.session_state.fc_flipped is False

    app.record_flashcard_review(1, is_known=False)
    assert app.st.session_state.fc_pos == 2
    assert app.st.session_state.fc_unknown == [1]


def test_quiz_score_calculation_logic() -> None:
    """Kiểm thử logic chấm điểm trắc nghiệm và chuẩn hoá đáp án linh hoạt."""
    study_set = app.normalize_study_set(SAMPLE_BACKEND_STUDY_SET)
    quizzes = study_set["quizzes"]

    # Giả lập người dùng trả lời đúng 3/4 câu (câu 2 truyền chữ cái 'B' vẫn khớp chính xác)
    user_answers = {
        0: quizzes[0]["correct_answer"],
        1: quizzes[1]["options"][0],  # Sai
        2: "B",                       # Đúng (khớp ký tự đầu)
        3: quizzes[3]["correct_answer"],
    }
    report = app.calculate_quiz_score(quizzes, user_answers)
    assert report["total"] == 4
    assert report["correct"] == 3
    assert report["wrong"] == 1
    assert report["pct"] == 75
    assert report["last_score"] == "3/4 (75%)"
    assert report["details"][0]["is_correct"] is True
    assert report["details"][1]["is_correct"] is False
    assert report["details"][2]["is_correct"] is True
    assert report["details"][3]["is_correct"] is True


def test_direct_api_v1_upload_and_error_alerts() -> None:
    """
    Kiểm thử tích hợp trực tiếp POST /api/v1/upload theo hợp đồng API của smart_note_backend,
    đọc thời gian xử lý thực (`X-Process-Time-Ms`), phủ toàn bộ mã lỗi trong Alert gợi ý và Toast động.
    """
    real_backend_201_payload = {
        "status": "success",
        "data": SAMPLE_BACKEND_STUDY_SET,
    }

    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.status_code = 201
    mock_response.headers = {"X-Process-Time-Ms": "4200"}
    mock_response.json.return_value = real_backend_201_payload

    with patch("app.requests.post", return_value=mock_response) as mock_post:
        res = app.api_upload(
            file_info={"name": "bai_giang_ai.pdf", "bytes": b"%PDF-1.4...", "type": "application/octet-stream"},
            subject="Trí tuệ nhân tạo (AI)",
            simulate_error=False,
            base_url="http://127.0.0.1:8000",
            flashcard_count=5,
            quiz_count=5,
        )
        mock_post.assert_called_once()
        endpoint_called = mock_post.call_args[0][0]
        sent_files = mock_post.call_args[1]["files"]
        sent_data = mock_post.call_args[1]["data"]

        assert endpoint_called == "http://127.0.0.1:8000/api/v1/upload"
        assert sent_files["file"][2] == "application/pdf"
        assert sent_data == {"flashcard_count": "5", "quiz_count": "5"}
        assert res["status"] == "success"
        assert res["duration_s"] == 4.2
        assert "4.2s" in res["meta"]["detail"]
        assert "MẠNG NƠ-RON NHÂN TẠO" in res["extracted_text"]
        assert len(res["data"]["flashcards"]) == 3
        assert res["data"]["flashcards"][0]["front_text"] == "Forward Propagation trong ANN làm nhiệm vụ gì?"
        assert res["data"]["quizzes"][0]["correct_answer"] == "Backpropagation"
        # Tự động tổng hợp bản tóm tắt từ dữ liệu thật khi Backend không trả trường summary
        assert "Forward Propagation" in res["data"]["summary"]

    # Kiểm thử fallback wall-clock khi response không có header X-Process-Time-Ms
    mock_no_header = MagicMock()
    mock_no_header.ok = True
    mock_no_header.status_code = 201
    mock_no_header.headers = {}
    mock_no_header.json.return_value = real_backend_201_payload
    with patch("app.requests.post", return_value=mock_no_header):
        res_wall = app.api_upload(
            file_info={"name": "slide.png", "bytes": b"PNG", "type": "image/png"},
            subject="Trí tuệ nhân tạo (AI)",
            simulate_error=False,
            base_url="http://127.0.0.1:8000",
        )
        assert res_wall["status"] == "success"
        assert isinstance(res_wall["duration_s"], float) and res_wall["duration_s"] >= 0.0

    # Kiểm thử xử lý chuẩn ErrorResponse từ smart_note_backend (HTTP 422 NO_TEXT_DETECTED)
    mock_err_response = MagicMock()
    mock_err_response.ok = False
    mock_err_response.status_code = 422
    mock_err_response.json.return_value = {
        "status": "error",
        "error": {
            "code": "NO_TEXT_DETECTED",
            "message": "Không phát hiện được chữ rõ ràng trong tệp tải lên.",
        },
    }
    with patch("app.requests.post", return_value=mock_err_response):
        err_res = app.api_upload(
            file_info={"name": "anh_mo.png", "bytes": b"PNG_DATA", "type": "image/png"},
            subject="Trí tuệ nhân tạo (AI)",
            simulate_error=False,
            base_url="http://127.0.0.1:8000",
        )
        assert err_res["status"] == "error"
        assert err_res["code"] == "NO_TEXT_DETECTED"
        assert "[NO_TEXT_DETECTED]" in err_res["message"]
        assert "Không phát hiện được chữ rõ ràng" in err_res["message"]

    # Kiểm thử lỗi mất kết nối Backend (BACKEND_UNREACHABLE) và Timeout (AI_TIMEOUT)
    with patch("app.requests.post", side_effect=requests.exceptions.ConnectionError("Connection refused")):
        conn_err = app.api_upload(
            file_info={"name": "anh_mo.png", "bytes": b"PNG_DATA", "type": "image/png"},
            subject="Trí tuệ nhân tạo (AI)",
            simulate_error=False,
            base_url="http://127.0.0.1:8000",
        )
        assert conn_err["status"] == "error"
        assert conn_err["code"] == "BACKEND_UNREACHABLE"
        assert "[BACKEND_UNREACHABLE]" in conn_err["message"]

    with patch("app.requests.post", side_effect=requests.exceptions.Timeout("Read timed out")):
        timeout_err = app.api_upload(
            file_info={"name": "anh_mo.png", "bytes": b"PNG_DATA", "type": "image/png"},
            subject="Trí tuệ nhân tạo (AI)",
            simulate_error=False,
            base_url="http://127.0.0.1:8000",
        )
        assert timeout_err["status"] == "error"
        assert timeout_err["code"] == "AI_TIMEOUT"
        assert "[AI_TIMEOUT]" in timeout_err["message"]

    # Kiểm thử độ phủ gợi ý tiếng Việt cho toàn bộ mã lỗi Backend quan trọng
    required_error_codes = [
        "AI_TIMEOUT",
        "FILE_TOO_LARGE",
        "IMAGE_TOO_LARGE",
        "NORMALIZED_IMAGE_TOO_LARGE",
        "PDF_TOO_MANY_PAGES",
        "AI_RATE_LIMITED",
        "AI_REQUEST_REJECTED",
        "AI_UPSTREAM_ERROR",
        "BACKEND_UNREACHABLE",
        "AI_NOT_CONFIGURED",
        "AI_AUTH_ERROR",
        "NO_TEXT_DETECTED",
    ]
    for code in required_error_codes:
        hint = app.get_error_hint(code)
        assert hint is not None, f"Thiếu hướng dẫn khắc phục cho mã lỗi {code}!"
        level, hint_msg, hint_icon = hint
        assert level in {"warning", "info"}
        assert "Gợi ý khắc phục" in hint_msg
        assert hint_icon.startswith(":material/")
        app.render_error_alert_with_hint(("extract", f"[{code}] Lỗi thử nghiệm", code))

    # Kiểm thử hàng đợi Toast động (queue_toast)
    app.queue_toast("Đã trích xuất văn bản thành công!", icon_name=":material/check_circle:")
    assert app.st.session_state.pending_toast == (
        "Đã trích xuất văn bản thành công!",
        ":material/check_circle:",
    )


def test_reset_to_new_upload_navigation() -> None:
    """Kiểm thử làm mới phiên để quay thẳng về Màn 1 (Tải lên file mới) từ Màn 4/5 hoặc Thư viện."""
    prev_key = app.st.session_state.get("uploader_key", 0)
    app.st.session_state.update({
        "nav_menu": "Thư viện",
        "current_screen": 5,
        "extracted_text": "Văn bản cũ",
        "draft_text": "Bản nháp cũ",
        "editor_text": "Bản nháp cũ",
        "pending_file": {"name": "cu.png", "size": 100, "bytes": b"123"},
        "uploaded_file_name": "cu.png",
        "api_error_state": ("extract", "Lỗi cũ", "AI_TIMEOUT"),
        "quiz_finished": True,
        "quiz_answers": {0: "A"},
        "fc_pos": 3,
        "fc_known": [0, 1],
    })
    app.reset_to_new_upload(notify=True)
    assert app.st.session_state.nav_menu == "Tạo mới"
    assert app.st.session_state.current_screen == 1
    assert app.st.session_state.extracted_text == ""
    assert app.st.session_state.draft_text == ""
    assert "editor_text" not in app.st.session_state
    assert app.st.session_state.pending_file is None
    assert app.st.session_state.api_error_state is None
    assert app.st.session_state.quiz_finished is False
    assert app.st.session_state.quiz_answers == {}
    assert app.st.session_state.fc_pos == 0
    assert app.st.session_state.uploader_key == prev_key + 1
    assert app.st.session_state.pending_toast is not None


if __name__ == "__main__":
    test_unique_streamlit_keys()
    print("[PASS] 1. Kiểm tra tính duy nhất của Streamlit widget keys")
    test_mock_json_completely_removed()
    print("[PASS] 2. Kiểm tra đã gỡ bỏ hoàn toàn Mock JSON & dead audio constants")
    test_fr14_upload_validation_aligned_with_backend()
    print("[PASS] 3. Kiểm thử đồng bộ FR14 Frontend <-> Backend (10 MB, JPG/JPEG/PNG/WEBP/PDF)")
    test_zero_fake_sleep_and_http_session_reuse()
    print("[PASS] 4. Kiểm thử loại bỏ hoàn toàn time.sleep & tái sử dụng HTTP Session")
    test_flashcard_flip_and_review_logic()
    print("[PASS] 5. Kiểm thử logic lật thẻ Flashcard & đánh giá Đã nhớ / Chưa nhớ")
    test_quiz_score_calculation_logic()
    print("[PASS] 6. Kiểm thử logic tính điểm Trắc nghiệm & so khớp đáp án")
    test_direct_api_v1_upload_and_error_alerts()
    print("[PASS] 7. Kiểm thử POST /api/v1/upload, X-Process-Time-Ms, Error Alert Hints & Toast động")
    test_reset_to_new_upload_navigation()
    print("[PASS] 8. Kiểm thử điều hướng Tạo mới / làm mới hoàn toàn về Màn 1")
    print("\n==> TẤT CẢ BÀI KIỂM THỬ ĐỀU THÀNH CÔNG (8/8 PASSED)!")
