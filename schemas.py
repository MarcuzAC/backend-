from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
import uuid
from datetime import datetime

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone_number: str = Field(..., pattern=r"^\+?[0-9\s\-]+$")

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone_number: Optional[str] = Field(None, pattern=r"^\+?[0-9\s\-]+$")
    password: Optional[str] = Field(None, min_length=8)

class UserResponse(UserBase):
    id: uuid.UUID
    is_admin: bool
    model_config = ConfigDict(from_attributes=True)

# Video Schemas
class VideoBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    category_id: uuid.UUID

class VideoCreate(VideoBase):
    pass

class VideoUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    category_id: Optional[uuid.UUID] = None
    
class VideoResponse(BaseModel):
    id: uuid.UUID
    title: str
    created_date: datetime
    vimeo_url: Optional[str] = None
    vimeo_id: Optional[str] = None
    category: Optional[str] = None
    thumbnail_url: Optional[str] = None
    like_count: int = 0
    comment_count: int = 0
    model_config = ConfigDict(from_attributes=True)

# Category Schemas
class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: uuid.UUID
    model_config = ConfigDict(from_attributes=True)

# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

# Like Schemas
class LikeBase(BaseModel):
    video_id: uuid.UUID

class LikeCreate(LikeBase):
    pass

class LikeResponse(LikeBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Comment Schemas
class CommentCreate(BaseModel):
    """Schema for creating a comment (user_id comes from auth token)"""
    video_id: uuid.UUID
    text: str = Field(..., min_length=1, max_length=500)

class CommentBase(BaseModel):
    """Base schema containing all comment fields"""
    video_id: uuid.UUID
    user_id: uuid.UUID
    text: str

class CommentResponse(BaseModel):
    """Schema for comment responses including user details"""
    id: uuid.UUID
    text: str
    created_at: datetime
    user: 'UserResponse'
    video_id: uuid.UUID
    model_config = ConfigDict(from_attributes=True)

class CommentMinimalResponse(BaseModel):
    """Minimal comment response without user details"""
    id: uuid.UUID
    text: str
    created_at: datetime
    user_id: uuid.UUID
    video_id: uuid.UUID
    model_config = ConfigDict(from_attributes=True)

# Fix circular reference
CommentResponse.model_rebuild()