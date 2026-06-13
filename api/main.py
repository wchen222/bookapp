from contextlib import asynccontextmanager

from pydantic_extra_types import isbn
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import FastAPI, status, Depends, Request, HTTPException
from typing import Annotated

from config import settings
from schemas import UserBase, BookBase, UserCreate, Token, BookResponse
from database import Base, engine, get_db
import models
from sqlalchemy import select
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles



from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.concurrency import run_in_threadpool

from auth import (
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

app = FastAPI(lifespan=lifespan)
#app.mount("/static", StaticFiles(directory="static"), name="static")


@app.exception_handler(StarletteHTTPException)
def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
    message = (
        exception.detail
        if exception.detail
        else "error"
    )

    #if request.url.path.startswith("/api"):
    return JSONResponse(content = {"detail": message}, status_code=exception.status_code)



@app.get("/")
async def root():
    return {"message": "Hello World"}



@app.post(
    "/api/books",
    response_model=BookBase,
    status_code=status.HTTP_201_CREATED
)
async def create_book(
        book: BookBase,
        db: Annotated[AsyncSession, Depends(get_db)]):

    new_book = models.Book(
        isbn=book.isbn,
        title=book.title,
        author=book.author,
        year=book.year,
    )
    db.add(new_book)
    await db.commit()
    await db.refresh(new_book)
    return book

@app.post(
    "/api/libraries",
    response_model=BookBase,
    status_code=status.HTTP_201_CREATED
)
async def add_book(
        target_isbn: str,
        current_user: CurrentUser,
        db: Annotated[AsyncSession, Depends(get_db)],
        reading_status: models.ReadingStatus | None = None,

):
    result = await db.execute(select(models.Book).where(models.Book.isbn == target_isbn))
    book = result.scalars().first()


    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")


    duplicate_check = await db.execute(
        select(models.UserBookLink)
        .where(models.UserBookLink.user_id == current_user.id,
               models.UserBookLink.book_id == book.id)
    )

    if duplicate_check.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Book already in library",
        )

    # add to library
    new_entry = models.UserBookLink(
        user_id = current_user.id,
        book_id=book.id,
        status = reading_status,
    )
    db.add(new_entry)
    await db.commit()
    return book


# write the end point to view private library

@app.get("/api/libraries",
          response_model=list[BookBase],
)
async def get_library(
        current_user: CurrentUser,
        db: Annotated[AsyncSession, Depends(get_db)]
):

    result = await db.execute(
        select(models.Book)
        .join(models.UserBookLink, models.Book.id == models.UserBookLink.book_id)
        .where(models.UserBookLink.user_id == current_user.id)
    )
    return result.scalars().all()



#write patch endpoint to update book status in library

@app.get("/api/books", response_model=list[BookResponse])
async def get_books(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.Book)
    )

    books = result.scalars().all()
    return books


#users
@app.get("/api/users", response_model=list[UserBase])
async def get_users(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.User)
    )
    users = result.scalars().all()
    return users

@app.post("/api/users", response_model=UserBase)
async def create_user(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    #add some checks here

    new_user = models.User(
        username = user.username,
        email = user.email.lower(),
        password_hash = hash_password(user.password),
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user) # come back for attributes
    return new_user



@app.post("/api/auth/token", response_model=Token)
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

@app.get("/api/users/me", response_model=UserBase)
async def get_current_user(current_user: CurrentUser):
    return current_user


#@app.delete()

