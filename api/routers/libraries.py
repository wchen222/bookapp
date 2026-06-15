from api.schemas import UserBase, BookBase, UserCreate, Token, BookResponse, LibraryBook, PaginatedResponse
from api.database import Base, engine, get_db
import api.models as models
from api.auth import CurrentUser
from api.services import get_book_query, check_book_exists, check_library_entry, make_paginated_query

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter()


@router.post(
    "",
    response_model=BookBase,
    status_code=status.HTTP_201_CREATED
)
async def add_book(
        target_isbn: str,
        current_user: CurrentUser,
        db: Annotated[AsyncSession, Depends(get_db)],
        reading_status: models.ReadingStatus | None = None,
):
    book = await check_book_exists(target_isbn, db)
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


@router.get("",
            response_model=PaginatedResponse[LibraryBook],
            status_code=status.HTTP_200_OK,
)
async def get_library(
        current_user: CurrentUser,
        db: Annotated[AsyncSession, Depends(get_db)],
        skip: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    query = get_book_query(current_user.id)
    return await make_paginated_query(db, query, skip, limit, is_scaler=False)


@router.patch("/{target_isbn}",
              response_model=LibraryBook)
async def update_book_status(
        target_isbn: str,
        new_reading_status: models.ReadingStatus,
        current_user: CurrentUser,
        db: Annotated[AsyncSession, Depends(get_db)]
):
    book = await check_book_exists(target_isbn, db)
    library_entry = await check_library_entry(current_user.id, book.id, db)
    library_entry.status = new_reading_status
    await db.commit()
    await db.refresh(library_entry)
    book_result = await db.execute(get_book_query(current_user.id).where(models.Book.isbn == target_isbn))
    return book_result.one()


@router.delete("/{target_isbn}",
               status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(
        target_isbn: str,
        current_user: CurrentUser,
        db: Annotated[AsyncSession, Depends(get_db)],
):
    book = await check_book_exists(target_isbn, db)
    library_entry = await check_library_entry(current_user.id, book.id, db)
    await db.delete(library_entry)
    await db.commit()

