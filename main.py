from contextlib import asynccontextmanager

from pydantic_extra_types import isbn
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import FastAPI, status, Depends, Request, HTTPException
from typing import Annotated

from api.config import settings
from api.schemas import UserBase, BookBase, UserCreate, Token, BookResponse
from api.database import Base, engine, get_db
import api.models as models
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.concurrency import run_in_threadpool
#from routers import users, libraries
from api.routers.libraries import router as libraries
from api.routers.users import router as users
from api.routers.books import router as books

from api.auth import (
    CurrentUser,
    create_access_token,
    hash_password,
    verify_password,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

app = FastAPI(lifespan=lifespan, swagger_ui_parameters={"tryItOutEnabled": True})
#app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(users, prefix="/api/users", tags=["Users"])
app.include_router(books, prefix="/api/books", tags=["Book Catalog"])
app.include_router(libraries, prefix="/api/libraries", tags=["My Library"])


@app.exception_handler(StarletteHTTPException)
def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
    message = (
        exception.detail
        if exception.detail
        else "error"
    )

    #if request.url.path.startswith("/api"):
    return JSONResponse(content = {"detail": message}, status_code=exception.status_code)



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


