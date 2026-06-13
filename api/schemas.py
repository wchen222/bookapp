


from pydantic import BaseModel, ConfigDict, EmailStr, Field


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


class BookResponse(BookBase):
    id: int

class Token(BaseModel):
    access_token: str
    token_type: str



