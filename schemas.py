from pydantic import BaseModel, EmailStr
from typing import Optional, List
import uuid
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    username: str
    first_name: str
    last_name: str
    phone_number: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

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
    avatar_url: Optional[str] = None
    # comments: Optional[List['CommentResponse']] = []  # Uncomment if needed

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
    thumbnail_url: Optional[str] = None
    like_count: Optional[int] = 0
    comment_count: Optional[int] = 0
    # comments: Optional[List['CommentResponse']] = []  # Uncomment if needed

    class Config:
        from_attributes = True

class CategoryBase(BaseModel):
    name: str

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: uuid.UUID
    video_count: Optional[int] = 0

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: uuid.UUID

class LikeBase(BaseModel):
    user_id: uuid.UUID
    video_id: uuid.UUID

class LikeCreate(LikeBase):
    pass

class LikeResponse(LikeBase):
    id: uuid.UUID
    created_at: datetime
    user: Optional[UserResponse] = None

    class Config:
        from_attributes = True

class CommentBase(BaseModel):
    text: str

class CommentCreate(BaseModel):
    video_id: uuid.UUID
    text: str

class CommentUpdate(BaseModel):
    text: str

class CommentResponse(BaseModel):
    id: uuid.UUID
    text: str
    user_id: uuid.UUID
    video_id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    user: UserResponse

    class Config:
        orm_mode = True

# Update forward references for circular dependencies
CommentResponse.update_forward_refs()
UserResponse.update_forward_refs()
VideoResponse.update_forward_refs()