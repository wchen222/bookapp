

from api.schemas import UserBase, BookBase, UserCreate, Token, BookResponse
from api.database import Base, engine, get_db
import api.models as models


from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import (
    CurrentUser,
    create_access_token,
    hash_password,
    verify_password,
)


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

@router.get("",
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



@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(
        target_isbn: str,
        current_user: CurrentUser,
        db: Annotated[AsyncSession, Depends(get_db)],
):

    book_result = await db.execute(select(models.Book).where(models.Book.isbn == target_isbn))
    book = book_result.scalars().first()

    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book Does Not Exist In Our Catalog",
        )

    entry_result = await db.execute(
        select(models.UserBookLink)
        .where(models.UserBookLink.user_id == current_user.id,
               models.UserBookLink.book_id == book.id)
    )
    library_entry = entry_result.scalars().first()

    if not library_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Library Entry Not Found",
        )

    await db.delete(library_entry)
    await db.commit()

