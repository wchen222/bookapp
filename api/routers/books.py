from api.schemas import UserBase, BookBase, UserCreate, Token, BookResponse, PaginatedResponse
from api.database import Base, engine, get_db
import api.models as models
from api.services import make_paginated_query


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


#async def get_book_helper(db: AsyncSession, skip: int, limit: int):


@router.get("/search", response_model=PaginatedResponse[BookBase])
async def search_books(
        book_title: str,
        db: Annotated[AsyncSession, Depends(get_db)],
        skip: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    query = (select(models.Book).where(models.Book.title.ilike(f"%{book_title}%")))
    return await make_paginated_query(db, query, skip, limit)


@router.get("",
            response_model=PaginatedResponse[BookBase])
async def get_books(
        db: Annotated[AsyncSession, Depends(get_db)],
        skip: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    query = select(models.Book)
    return await make_paginated_query(db, query, skip, limit)




