class APIError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(code)


def error_body(code: str, message: str):
    return {"status": "error", "error": {"code": code, "message": message}}
