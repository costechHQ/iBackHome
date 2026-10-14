"""The FastAPI application. Owner: Christopher.

Nobody edits this file to add endpoints: every `router.py` under app/base/ and app/features/
that defines `router = APIRouter(...)` is mounted under /api/v1 automatically (core/discovery.py).
/healthz stays at the root so load balancers and docker can reach it without the API prefix.
"""

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import health, observability
from app.core.config import get_settings
from app.core.discovery import import_all
from app.core.errors import register_error_handlers
from app.core.models_registry import load_all_models

API_PREFIX = "/api/v1"


def build_api_router() -> APIRouter:
    api = APIRouter(prefix=API_PREFIX)
    for module in import_all("router"):
        router = getattr(module, "router", None)
        if isinstance(router, APIRouter):
            api.include_router(router)
    return api


def create_app() -> FastAPI:
    settings = get_settings()
    observability.configure_logging(settings)
    observability.init_sentry(settings, "api")
    # Load every table first so relationships between features resolve before the first query.
    load_all_models()

    # `debug` is deliberately not passed: it would replace our JSON 500 response with an HTML traceback.
    app = FastAPI(title=settings.app_name)
    register_error_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[observability.REQUEST_ID_HEADER],  # so the web app can show it in error reports
    )
    # Added last, so it runs first: every request (CORS preflights included) gets an ID and a log line.
    app.add_middleware(observability.RequestIdMiddleware)
    app.include_router(health.router)
    app.include_router(build_api_router())
    return app


app = create_app()
