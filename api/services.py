import api.models as models
import uuid
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from api.schemas import PaginatedResponse



def get_book_query(user_id):
    query = (select(models.Book.isbn,
               models.Book.title,
               models.Book.author,
               models.Book.year,
               models.UserBookLink.status)
        .join(models.UserBookLink, models.Book.id == models.UserBookLink.book_id)
        .where(models.UserBookLink.user_id == user_id)
    )
    return query


async def check_book_exists(target_isbn: str, db: AsyncSession):
    book_result = await db.execute(select(models.Book).where(models.Book.isbn == target_isbn))
    book = book_result.scalars().first()

    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book Does Not Exist In Our Catalog",
        )

    return book


async def check_library_entry(user_id: uuid.UUID, book_id: int, db: AsyncSession):
    result = await db.execute(
        select(models.UserBookLink)
        .where(models.UserBookLink.user_id == user_id,
               models.UserBookLink.book_id == book_id)
    )

    library_entry = result.scalars().first()

    if not library_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Library Entry Not Found",
        )

    return library_entry


async def make_paginated_query(db: AsyncSession,
                            base_query,
                            skip: int,
                            limit: int,
                            is_scaler: bool = True
):
    count_result = await db.execute(select(func.count()).select_from(base_query.subquery()))
    total = count_result.scalar() or 0
    result = await db.execute(
        base_query.offset(skip).limit(limit)
    )
    if is_scaler:
        items = list(result.scalars().all())
    else:
        items = list(result.all())

    has_more = skip + len(items) < total
    return PaginatedResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
        has_more=has_more,
    )