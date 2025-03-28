from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Union
import uuid
from datetime import datetime

# Utility schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    id: Optional[str] = None

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    phone_number: str = Field(..., min_length=10, max_length=15)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    first_name: Optional[str] = Field(None, min_length=2, max_length=50)
    last_name: Optional[str] = Field(None, min_length=2, max_length=50)
    phone_number: Optional[str] = Field(None, min_length=10, max_length=15)
    password: Optional[str] = Field(None, min_length=8)

class UserResponse(UserBase):
    id: uuid.UUID
    is_admin: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Auth schemas
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

# Category schemas
class CategoryBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: uuid.UUID
    created_at: datetime
    video_count: Optional[int] = 0

    class Config:
        from_attributes = True

# Video schemas
class VideoBase(BaseModel):
    title: str = Field(..., min_length=5, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    category_id: uuid.UUID

class VideoCreate(VideoBase):
    pass

class VideoUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=5, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    category_id: Optional[uuid.UUID] = None

class VideoResponse(VideoBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    vimeo_url: Optional[str] = None
    vimeo_id: Optional[str] = None
    thumbnail_url: Optional[str] = None
    likes_count: int = 0
    comments_count: int = 0
    category: Optional[CategoryResponse] = None
    is_liked: Optional[bool] = False  # For authenticated user check

    class Config:
        from_attributes = True

# Like schemas
class LikeBase(BaseModel):
    pass

class LikeCreate(LikeBase):
    pass

class LikeResponse(LikeBase):
    id: uuid.UUID
    user_id: uuid.UUID
    video_id: uuid.UUID
    created_at: datetime
    user: Optional[UserResponse] = None

    class Config:
        from_attributes = True

# Comment schemas
class CommentBase(BaseModel):
    content: str = Field(..., min_length=1, max_length=500)

class CommentCreate(CommentBase):
    pass

class CommentResponse(CommentBase):
    id: uuid.UUID
    user_id: uuid.UUID
    video_id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    user: Optional[UserResponse] = None

    class Config:
        from_attributes = True

# Extended video response with relationships
class VideoDetailResponse(VideoResponse):
    likes: List[LikeResponse] = []
    comments: List[CommentResponse] = []

    class Config:
        from_attributes = True

# Pagination schemas
class PaginatedResponse(BaseModel):
    total: int
    page: int
    per_page: int
    items: List[Union[VideoResponse, UserResponse, CommentResponse]]

# Analytics schemas
class AnalyticsResponse(BaseModel):
    total_videos: int
    total_users: int
    total_likes: int
    total_comments: int
    popular_videos: List[VideoResponse]
    recent_activity: List[Union[CommentResponse, LikeResponse]]

# Update forward references for recursive models
VideoResponse.update_forward_refs()
VideoDetailResponse.update_forward_refs()
CommentResponse.update_forward_refs()