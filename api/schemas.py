


from pydantic import BaseModel, ConfigDict, EmailStr, Field
from api.models import ReadingStatus


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
    reading_status: ReadingStatus


class BookResponse(BookBase):
    id: int

class Token(BaseModel):
    access_token: str
    token_type: str



