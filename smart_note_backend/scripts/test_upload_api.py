"""Call a real running backend. This script invokes the configured paid AI provider."""
import argparse
import mimetypes
from pathlib import Path

import httpx

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload ảnh/PDF tới API thật")
    parser.add_argument("file", type=Path)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--flashcards", type=int, default=5)
    parser.add_argument("--quizzes", type=int, default=5)
    parser.add_argument("--user-id")
    args = parser.parse_args()
    fields = {"flashcard_count": str(args.flashcards), "quiz_count": str(args.quizzes)}
    if args.user_id:
        fields["user_id"] = args.user_id
    with args.file.open("rb") as stream:
        result = httpx.post(args.url.rstrip("/") + "/api/v1/upload", data=fields,
                            files={"file": (args.file.name, stream, mimetypes.guess_type(args.file.name)[0]
                                             or "application/octet-stream")}, timeout=150)
    print("HTTP", result.status_code)
    import json
    print(json.dumps(result.json(), ensure_ascii=False, indent=2))
    raise SystemExit(0 if result.is_success else 1)
