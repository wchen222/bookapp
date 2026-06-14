
from api.schemas import UserBase, BookBase, UserCreate, Token, BookResponse
from api.database import Base, engine, get_db
import api.models as models


from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


from api.auth import (
    CurrentUser,
    create_access_token,
    hash_password,
    verify_password,
)


router = APIRouter()


#users

@router.post("", response_model=UserBase)
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


@router.get("/me", response_model=UserBase)
async def get_current_user(current_user: CurrentUser):
    return current_user

@router.get("", response_model=list[UserBase])
async def get_users(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.User)
    )
    users = result.scalars().all()
    return users