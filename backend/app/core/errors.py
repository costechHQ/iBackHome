"""One error shape for the whole API:

    {"error": {"code": "milestone_not_verified", "message": "..."}}

Raise it from any service:

    raise AppError("milestone_not_verified", "This milestone has not been verified yet.", 409)
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def error_body(code: str, message: str) -> dict[str, dict[str, str]]:
    return {"error": {"code": code, "message": message}}


async def _app_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return JSONResponse(status_code=exc.status_code, content=error_body(exc.code, exc.message))


async def _http_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    code = {
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
    }.get(exc.status_code, "http_error")
    return JSONResponse(status_code=exc.status_code, content=error_body(code, str(exc.detail)))


async def _validation_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    first = exc.errors()[0] if exc.errors() else {}
    where = ".".join(str(p) for p in first.get("loc", []))
    message = f"{where}: {first.get('msg', 'invalid request')}" if where else "invalid request"
    return JSONResponse(status_code=422, content=error_body("validation_error", message))


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
