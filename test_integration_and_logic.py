"""
Bộ kiểm thử tự động (Unit & Integration Tests) cho Smart Note & Quizzify:
  1. Kiểm tra tính duy nhất của toàn bộ Streamlit widget/container keys trong `app.py`.
  2. Kiểm tra việc gỡ bỏ hoàn toàn Mock JSON (`mock_data.json`, `load_mock_json`, `mock_api_upload`).
  3. Kiểm thử logic lật thẻ (flip) & đánh giá thẻ Đã nhớ / Chưa nhớ (Màn 4).
  4. Kiểm thử logic tính điểm Trắc nghiệm & chuẩn hoá đáp án (Màn 5).
  5. Kiểm thử tích hợp trực tiếp Endpoint `POST /api/v1/upload` từ FastAPI Backend + hệ thống Toast / Alert động.

Chạy: python test_integration_and_logic.py
"""

import ast
import collections
import logging
import sys
from pathlib import Path
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
    """Đảm bảo file mock_data.json và các hàm Mock JSON đã được gỡ bỏ hoàn toàn."""
    assert not Path("mock_data.json").exists(), "File mock_data.json vẫn còn tồn tại!"
    assert not hasattr(app, "load_mock_json"), "Hàm load_mock_json vẫn còn trong app.py!"
    assert not hasattr(app, "mock_api_upload"), "Hàm mock_api_upload vẫn còn trong app.py!"
    assert not hasattr(app, "API_MODE_MOCK"), "Hằng số API_MODE_MOCK vẫn còn trong app.py!"


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
    Kiểm thử tích hợp trực tiếp POST /api/v1/upload theo hợp đồng API của smart_note_backend
    cùng hệ thống Toast / Alert động khi xảy ra lỗi.
    """
    real_backend_201_payload = {
        "status": "success",
        "data": SAMPLE_BACKEND_STUDY_SET,
    }

    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.status_code = 201
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
        assert "MẠNG NƠ-RON NHÂN TẠO" in res["extracted_text"]
        assert len(res["data"]["flashcards"]) == 3
        assert res["data"]["flashcards"][0]["front_text"] == "Forward Propagation trong ANN làm nhiệm vụ gì?"
        assert res["data"]["quizzes"][0]["correct_answer"] == "Backpropagation"
        # Tự động tổng hợp bản tóm tắt từ dữ liệu thật khi Backend không trả trường summary
        assert "Forward Propagation" in res["data"]["summary"]

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

    # Kiểm thử lỗi mất kết nối Backend (BACKEND_UNREACHABLE)
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

    # Kiểm thử hàng đợi Toast động (queue_toast)
    app.queue_toast("Đã trích xuất văn bản thành công!", icon_name=":material/check_circle:")
    assert app.st.session_state.pending_toast == (
        "Đã trích xuất văn bản thành công!",
        ":material/check_circle:",
    )


if __name__ == "__main__":
    test_unique_streamlit_keys()
    print("[PASS] 1. Kiểm tra tính duy nhất của Streamlit widget keys")
    test_mock_json_completely_removed()
    print("[PASS] 2. Kiểm tra đã gỡ bỏ hoàn toàn Mock JSON (mock_data.json & mock functions)")
    test_flashcard_flip_and_review_logic()
    print("[PASS] 3. Kiểm thử logic lật thẻ Flashcard & đánh giá Đã nhớ / Chưa nhớ")
    test_quiz_score_calculation_logic()
    print("[PASS] 4. Kiểm thử logic tính điểm Trắc nghiệm & so khớp đáp án")
    test_direct_api_v1_upload_and_error_alerts()
    print("[PASS] 5. Kiểm thử tích hợp trực tiếp POST /api/v1/upload & Toast/Alert động")
    print("\n==> TẤT CẢ BÀI KIỂM THỬ ĐỀU THÀNH CÔNG (5/5 PASSED)!")
