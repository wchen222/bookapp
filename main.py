import json
from contextlib import asynccontextmanager
import faiss
import numpy as np
from fastapi import FastAPI, Request
from api.config import settings
from api.schemas import Token
from api.database import engine, get_db
import api.models as models
from starlette.exceptions import HTTPException as StarletteHTTPException
from datetime import timedelta
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from api.routers.libraries import router as libraries
from api.routers.users import router as users
from api.routers.books import router as books
from api.auth import create_access_token, verify_password
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address


@asynccontextmanager
async def lifespan(_app: FastAPI):
    #  recommendation model setup
    app.state.faiss_index = faiss.read_index("ml/engine/artifacts/items.index")
    app.state.item_embeddings = np.load("ml/engine/artifacts/item_embeddings.npy")
    with open("ml/engine/artifacts/mappings.json", "r") as f:
        app.state.mappings = json.load(f)
    yield
    del app.state.faiss_index
    del app.state.item_embeddings
    await engine.dispose()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["60/minute"]
)
app = FastAPI(lifespan=lifespan, swagger_ui_parameters={"tryItOutEnabled": True})
app.include_router(users, prefix="/api/users", tags=["Users"])
app.include_router(books, prefix="/api/books", tags=["Book Catalog"])
app.include_router(libraries, prefix="/api/libraries", tags=["My Library"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(StarletteHTTPException)
def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
    message = (
        exception.detail
        if exception.detail
        else "error"
    )
    return JSONResponse(content={"detail": message}, status_code=exception.status_code)


@app.get("/")
def read_root():
    return {"status": "ok", "message": "Book Engine API is running"}


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "SAME ORIGIN"
    response.headers["X-Content-Type-Options"] = "nosniff"
    if "Referrer-Policy" not in response.headers:
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if request.url.hostname not in ("localhost", "127.0.0.1"):
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains"
        )
    return response

@app.get("/health")
async def health_check(db: Annotated[AsyncSession, Depends(get_db)]):
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database Error"
        ) from exc
    return {"status": "healthy"}


@app.post("/api/auth/token", response_model=Token, tags=["Authentication"])
async def login_for_access_token(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
        db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(models.User).where(
            func.lower(models.User.email) == form_data.username.lower(),
        ),
    )
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token, token_type="bearer")
