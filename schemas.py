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
        orm_mode = True

class VideoBase(BaseModel):
    title: str
    category_id: uuid.UUID

class VideoCreate(VideoBase):
    pass

class VideoUpdate(BaseModel):
    title: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    
class VideoResponse(BaseModel):
    id: uuid.UUID
    title: str
    created_date: datetime
    vimeo_url: Optional[str] = None
    vimeo_id: Optional[str] = None
    category: Optional[str] = None 

    class Config:
        from_attributes = True

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

    # Like Schemas
class LikeBase(BaseModel):
    user_id: uuid.UUID
    video_id: uuid.UUID

class LikeCreate(LikeBase):
    pass

class LikeResponse(LikeBase):
    id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True

# Comment Schemas
class CommentBase(BaseModel):
    user_id: uuid.UUID
    video_id: uuid.UUID
    text: str

class CommentCreate(CommentBase):
    pass

class CommentResponse(CommentBase):
    id: uuid.UUID
    created_at: datetime
    user: UserResponse  # Include user details in the response

    class Config:
        from_attributes = True