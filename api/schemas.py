from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from typing import Generic, TypeVar
from api.models import ReadingStatus

T = TypeVar("T")

class UserBase(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    email: EmailStr = Field(min_length=1, max_length=100)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=100)


class BookBase(BaseModel):
    isbn: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=100)
    author: str = Field(min_length=1, max_length=50)
    year: int


class LibraryBook(BookBase):
    model_config = ConfigDict(from_attributes=True)
    status: ReadingStatus
    rating: int

class AddLibraryBook(BaseModel):
    isbn: str = Field(min_length=1, max_length=100)
    status: ReadingStatus = ReadingStatus.UNREAD
    rating: int = Field(default=0, ge=0, le=10)
    notes: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def check_combination(self) -> "AddLibraryBook":
        if self.status == "unread" and self.rating != 0:
            raise ValueError("Rating cannot be set on an unread book")
        return self


class BookResponse(BookBase):
    id: int


class Token(BaseModel):
    access_token: str
    token_type: str


class PaginatedResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(from_attributes=True)
    items: list[T]
    total: int
    skip: int
    limit: int
    has_more: bool

