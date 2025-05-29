from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_validator
from typing import Optional, List
import uuid
from datetime import datetime
import re

class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    phone_number: str = Field(..., min_length=10, max_length=15)

    @field_validator('phone_number')
    def validate_phone_number(cls, v):
        if not re.match(r'^\+?[0-9]{10,15}$', v):
            raise ValueError('Invalid phone number format')
        return v

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=32, max_length=32)
    new_password: str = Field(..., min_length=8)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    phone_number: Optional[str] = Field(None, min_length=10, max_length=15)
    password: Optional[str] = Field(None, min_length=8)

    @field_validator('phone_number')
    def validate_phone_number(cls, v):
        if v is not None and not re.match(r'^\+?[0-9]{10,15}$', v):
            raise ValueError('Invalid phone number format')
        return v

class UserResponse(UserBase):
    id: uuid.UUID
    is_admin: bool = False
    avatar_url: Optional[str] = Field(None, max_length=255)
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class VideoBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    category_id: uuid.UUID

class VideoCreate(VideoBase):
    pass

class VideoUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    category_id: Optional[uuid.UUID] = None
    thumbnail_url: Optional[str] = Field(None, max_length=255)

class VideoResponse(VideoBase):
    id: uuid.UUID
    created_date: datetime
    vimeo_url: Optional[str] = Field(None, max_length=255)
    vimeo_id: Optional[str] = Field(None, max_length=50)
    category: Optional[str] = Field(None, max_length=100)
    thumbnail_url: Optional[str] = Field(None, max_length=255)
    like_count: int = 0
    comment_count: int = 0

    model_config = ConfigDict(from_attributes=True)

class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: uuid.UUID
    video_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: uuid.UUID
    expires_at: datetime

class LikeBase(BaseModel):
    user_id: uuid.UUID
    video_id: uuid.UUID

class LikeCreate(LikeBase):
    pass

class LikeResponse(LikeBase):
    id: uuid.UUID
    created_at: datetime
    user: Optional[UserResponse] = None
    video: Optional[VideoResponse] = None

    model_config = ConfigDict(from_attributes=True)

class CommentBase(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)

class CommentCreate(BaseModel):
    video_id: uuid.UUID
    text: str = Field(..., min_length=1, max_length=500)

class CommentUpdate(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)

class CommentResponse(BaseModel):
    id: uuid.UUID
    text: str
    user_id: uuid.UUID
    video_id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    user: UserResponse
    video: Optional[VideoResponse] = None

    model_config = ConfigDict(from_attributes=True)

class NewsBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1)  # No upper limit on content length
    is_published: bool = False

class NewsCreate(NewsBase):
    image_url: Optional[str] = Field(
        None, 
        max_length=255, 
        description="URL of the news image"
    )

class NewsUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    content: Optional[str] = Field(None, min_length=1)  # No upper limit
    image_url: Optional[str] = Field(
        None, 
        max_length=255, 
        description="URL of the news image"
    )
    is_published: Optional[bool] = None

class NewsResponse(NewsBase):
    id: uuid.UUID
    image_url: Optional[str] = Field(None, max_length=255)
    author_id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    author: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)

class NewsListResponse(BaseModel):
    items: List[NewsResponse]
    total: int
    page: int
    size: int