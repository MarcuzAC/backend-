from pydantic import BaseModel, EmailStr
from typing import Optional
import uuid
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    username: str
    first_name: str
    last_name: str
    phone_number: str

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    password: Optional[str] = None

class UserResponse(UserBase):
    id: uuid.UUID
    is_admin: bool

    class Config:
        from_attribute = True

class VideoBase(BaseModel):
    title: str
    category_id: uuid.UUID

class VideoCreate(VideoBase):
    pass

class VideoResponse(VideoBase):
    id: uuid.UUID
    created_date: datetime
    vimeo_url: str
    vimeo_id: str

    class Config:
        orm_mode = True

class CategoryBase(BaseModel):
    name: str

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: uuid.UUID

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str