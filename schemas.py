from pydantic import BaseModel, EmailStr, Field
from typing import Optional
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
    #user_id: uuid.UUID

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
        orm_mode = True

class VideoSearchRequest(BaseModel):
    query: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Text to search in video titles"
    )
    category_id: Optional[uuid.UUID] = Field(
        None,
        description="Filter by category ID"
    )
    page: int = Field(
        1,
        ge=1,
        description="Page number for pagination"
    )
    limit: int = Field(
        10,
        ge=1,
        le=100,
        description="Items per page"
    )


class VideoSearchResult(BaseModel):
    id: uuid.UUID
    title: str
    created_date: datetime
    vimeo_url: str
    vimeo_id: str
    thumbnail_url: Optional[str]
    category: str
    like_count: int
    comment_count: int

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class SearchSuggestion(BaseModel):
        suggestions: list[str] = Field(
        ...,
        description="List of autocomplete suggestions"
    )
class PopularSearches(BaseModel):
    terms: list[str] = Field(
        ...,
        description="List of popular search terms"
    )
