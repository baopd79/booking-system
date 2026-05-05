"""
Custom exceptions — map sang HTTP status ở exception handler.

Pattern: Service layer raise domain exception, không raise HTTPException trực tiếp.
Lý do: Service không nên biết về HTTP. Khi cần dùng service ở context khác
(CLI, background job), exception vẫn dùng được.

Naming: theo PEP 8, exception class kết thúc bằng `Error`.
"""


class AppError(Exception):
    """Base error — tất cả custom error kế thừa từ đây."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    message: str = "Internal server error"

    def __init__(
        self,
        message: str | None = None,
        error_code: str | None = None,
        details: dict | None = None,
    ):
        self.message = message or self.message
        self.error_code = error_code or self.error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(AppError):
    status_code = 400
    error_code = "VALIDATION_ERROR"
    message = "Validation failed"


class UnauthorizedError(AppError):
    status_code = 401
    error_code = "UNAUTHORIZED"
    message = "Authentication required"


class ForbiddenError(AppError):
    status_code = 403
    error_code = "FORBIDDEN"
    message = "Permission denied"


class NotFoundError(AppError):
    status_code = 404
    error_code = "NOT_FOUND"
    message = "Resource not found"


class ConflictError(AppError):
    status_code = 409
    error_code = "CONFLICT"
    message = "Resource conflict"


class GoneError(AppError):
    status_code = 410
    error_code = "GONE"
    message = "Resource no longer available"


class UnprocessableError(AppError):
    status_code = 422
    error_code = "UNPROCESSABLE"
    message = "Cannot process request"


class RateLimitError(AppError):
    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"
    message = "Too many requests"
