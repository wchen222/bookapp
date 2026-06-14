from api.schemas import UserBase, BookBase, UserCreate, Token, BookResponse
from api.database import Base, engine, get_db
import api.models as models


from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter()
@router.get("/search", response_model=list[BookBase])
async def search_books(
        book_title: str,
        db: Annotated[AsyncSession, Depends(get_db)]
):
    result = await db.execute(select(models.Book).where(models.Book.title.ilike(f"%{book_title}%")))
    return result.scalars().all()




@router.post(
    "",
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

#write patch endpoint to update book status in library

@router.get("", response_model=list[BookResponse])
async def get_books(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.Book)
    )

    books = result.scalars().all()
    return books
