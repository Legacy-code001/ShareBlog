from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, EmailStr

class UserBase(BaseModel):
    #UserBase model uses Pydantic to validate user data with correct field constraints.
    username: str = Field(min_length=1, max_length=100)
    email: EmailStr = Field(max_length=100)


class UserCreate(UserBase): 
    password: str = Field(min_length=8)

class UserPublic(BaseModel): 
    #tells Pydantic v2 to read data from standard class objects and database rows using their attributes instead of dictionaries
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    image_file: str | None
    image_path: str


class UserPrivate(BaseModel): 
    #tells Pydantic v2 to read data from standard class objects and database rows using their attributes instead of dictionaries
    email: EmailStr

class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = Field(default=None,max_length=120)
    image_file: str | None = Field(default=None, min_length=1, max_length=200)


class Token(BaseModel):
    access_token: str
    token_type: str
    
class PostBase(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)


class PostCreate(PostBase):
    user_id: int #temporary


class PostResponse(PostBase):
    #pydantic was able to read property from the sqlalchemy database
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    date_posted: datetime
    author: UserPublic

class PostUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    content: str | None = Field(default=None, min_length=1)

