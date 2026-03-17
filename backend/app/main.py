import logging
from time import perf_counter
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import ApplicationError, application_error_handler
from app.core.limiter import limiter

_MAX_BODY_BYTES = 12 * 1024 * 1024  # 12 MB — large enough for base64 face images
_REQUEST_LOGGER = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    if settings.face_model_warmup:
        # Pre-load InsightFace model at startup so the first request is not slow.
        # Never block startup if the model is unavailable.
        try:
            from app.services.face import FaceAnalyzer  # noqa: PLC0415
            FaceAnalyzer.get()
        except Exception:  # noqa: BLE001
            pass
    yield


def create_application() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )

    # ------------------------------------------------------------------ #
    # Rate-limiting state — must be set before any route handlers run.   #
    # ------------------------------------------------------------------ #
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    application.add_middleware(SlowAPIMiddleware)

    # ------------------------------------------------------------------ #
    # CORS                                                                 #
    # ------------------------------------------------------------------ #
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_origin_regex=settings.local_dev_cors_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.add_exception_handler(ApplicationError, application_error_handler)
    application.include_router(api_router, prefix=settings.api_v1_prefix)

    @application.middleware("http")
    async def enforce_body_size(request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > _MAX_BODY_BYTES:
            return JSONResponse(
                status_code=413,
                content={
                    "error": {
                        "code": "payload_too_large",
                        "message": f"Request body exceeds the {_MAX_BODY_BYTES // 1024 // 1024} MB limit.",
                    }
                },
            )
        return await call_next(request)

    @application.middleware("http")
    async def log_requests(request: Request, call_next):
        started = perf_counter()
        client_host = request.client.host if request.client else "unknown"
        try:
            response = await call_next(request)
        except Exception:
            _REQUEST_LOGGER.exception(
                "request_failed method=%s path=%s client=%s duration_ms=%.2f",
                request.method,
                request.url.path,
                client_host,
                (perf_counter() - started) * 1000,
            )
            raise

        _REQUEST_LOGGER.info(
            "request_completed method=%s path=%s status=%s client=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            client_host,
            (perf_counter() - started) * 1000,
        )
        return response

    @application.get("/health", tags=["health"])
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_application()