from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from omnikb.api.routes import router
from omnikb.config.settings import get_settings
from omnikb.middleware.request_timing import RequestTimingMiddleware

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
allowed_origins = [origin.strip() for origin in settings.cors_allowed_origins.split(",") if origin]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-Duration-Ms", "X-Correlation-Id"],
)
app.add_middleware(RequestTimingMiddleware)
app.include_router(router)
