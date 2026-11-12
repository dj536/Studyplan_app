"""FastAPI application entry point for ``uvicorn backend.main:app``."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend import models  # noqa: F401 - registers ORM tables with Base.metadata
from backend.api.routes import availability, chapters, courses, deadlines, documents, planning
from backend.database import Base, engine


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Create missing tables before serving requests."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="StudyPlan API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    """Keep HTTP errors in the same JSON detail envelope."""
    detail = exc.detail if isinstance(exc.detail, str) else "Une erreur est survenue"
    return JSONResponse(status_code=exc.status_code, content={"detail": detail}, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, _exc: RequestValidationError) -> JSONResponse:
    """Return a concise, uniform response for invalid request payloads."""
    return JSONResponse(status_code=422, content={"detail": "Données invalides"})


@app.exception_handler(Exception)
async def unexpected_exception_handler(_request: Request, _exc: Exception) -> JSONResponse:
    """Avoid exposing internal exception details or stack traces to clients."""
    return JSONResponse(status_code=500, content={"detail": "Erreur interne du serveur"})


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Report that the API process is responsive."""
    return {"status": "ok"}


for route_module in (courses, chapters, deadlines, availability, documents, planning):
    app.include_router(route_module.router)
