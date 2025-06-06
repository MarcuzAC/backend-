import json
import os
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import (
    APIRouter, 
    Depends, 
    File, 
    Form, 
    HTTPException, 
    status, 
    UploadFile,
    Query
)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from supabase import Client

from config import settings
from database import get_db
from models import News, User
from schemas import (
    NewsCreate, 
    NewsUpdate, 
    NewsResponse, 
    NewsListResponse
)
from auth import get_current_user

router = APIRouter(prefix="/news", tags=["news"])

# Helper Functions
def get_supabase() -> Client:
    """Dependency for Supabase client"""
    return settings.supabase

async def save_upload_file(file: UploadFile, supabase: Client) -> str:
    """Upload file to storage and return URL"""
    try:
        # Validate file type
        allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only image files (JPEG, PNG, GIF, WEBP) are allowed"
            )

        # Validate file size (max 5MB)
        max_size = 5 * 1024 * 1024  # 5MB
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset pointer
        if file_size > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size exceeds 5MB limit"
            )

        file_ext = os.path.splitext(file.filename)[1]
        file_name = f"{uuid.uuid4()}{file_ext}"
        
        contents = await file.read()
        res = supabase.storage.from_(settings.SUPABASE_BUCKET).upload(
            file=contents,
            path=file_name,
            file_options={"content-type": file.content_type}
        )
        
        url = supabase.storage.from_(settings.SUPABASE_BUCKET).get_public_url(file_name)
        return url
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}"
        )

async def delete_image_from_storage(image_url: str, supabase: Client):
    """Delete image from storage"""
    if not image_url:
        return
        
    try:
        filename = image_url.split('/')[-1]
        supabase.storage.from_(settings.SUPABASE_BUCKET).remove([filename])
    except Exception as e:
        print(f"Failed to delete image: {str(e)}")

async def get_news_or_404(
    news_id: uuid.UUID, 
    db: Session = Depends(get_db),
    check_owner: bool = True,
    current_user: User = Depends(get_current_user)
) -> News:
    """Dependency to get news item and validate ownership"""
    news = db.query(News).filter(News.id == news_id).first()
    if not news:
        raise HTTPException(status_code=404, detail="News item not found")
    
    if check_owner and news.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to access this news item")
    
    return news

# Endpoints
@router.post("/", response_model=NewsResponse)
async def create_news(
    news_data: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    image: Optional[UploadFile] = File(None),
    supabase: Client = Depends(get_supabase)
):
    """Create a new news article with optional image"""
    try:
        try:
            news_dict = json.loads(news_data)
            news_data = NewsCreate(**news_dict)
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid news_data format"
            )
        
        image_url = None
        if image:
            image_url = await save_upload_file(image, supabase)
        
        db_news = News(
            title=news_data.title,
            content=news_data.content,
            image_url=image_url,
            is_published=news_data.is_published,
            author_id=current_user.id
        )
        
        db.add(db_news)
        db.commit()
        db.refresh(db_news)
        return db_news
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/", response_model=NewsListResponse)
def get_news_list(
    page: int = Query(1, gt=0),
    size: int = Query(10, gt=0, le=100),
    published_only: bool = Query(True),
    db: Session = Depends(get_db)
):
    """Get paginated list of news items"""
    try:
        query = db.query(News)
        
        if published_only:
            query = query.filter(News.is_published == True)
        
        total = query.count()
        items = query.order_by(News.created_at.desc())\
                     .offset((page - 1) * size)\
                     .limit(size)\
                     .all()
        
        return NewsListResponse(
            items=items,
            total=total,
            page=page,
            size=size
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching news list: {str(e)}"
        )

@router.get("/search", response_model=NewsListResponse)
def search_news(
    query: str = Query(..., min_length=1, description="Search term"),
    page: int = Query(1, gt=0),
    size: int = Query(10, gt=0, le=100),
    published_only: bool = Query(True),
    db: Session = Depends(get_db)
):
    """Search news articles by title or content"""
    try:
        search = f"%{query}%"
        db_query = db.query(News).filter(
            or_(
                News.title.ilike(search),
                News.content.ilike(search)
            )
        )
        
        if published_only:
            db_query = db_query.filter(News.is_published == True)
        
        total = db_query.count()
        items = db_query.order_by(News.created_at.desc())\
                        .offset((page - 1) * size)\
                        .limit(size)\
                        .all()
        
        return NewsListResponse(
            items=items,
            total=total,
            page=page,
            size=size
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching news: {str(e)}"
        )

@router.get("/{news_id}", response_model=NewsResponse)
def get_news(
    news: News = Depends(get_news_or_404),
):
    """Get a single news item by ID"""
    return news

@router.put("/{news_id}", response_model=NewsResponse)
async def update_news(
    news_update: str = Form(...),
    news: News = Depends(get_news_or_404),
    db: Session = Depends(get_db),
    image: Optional[UploadFile] = File(None),
    supabase: Client = Depends(get_supabase)
):
    """Update a news item with optional image update"""
    try:
        try:
            update_data = json.loads(news_update)
            news_update = NewsUpdate(**update_data)
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid news_data format"
            )

        if image:
            if news.image_url:
                await delete_image_from_storage(news.image_url, supabase)
            news.image_url = await save_upload_file(image, supabase)

        if news_update.title is not None:
            news.title = news_update.title
        if news_update.content is not None:
            news.content = news_update.content
        if news_update.is_published is not None:
            news.is_published = news_update.is_published
        
        news.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(news)
        return news

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update news item: {str(e)}"
        )

@router.delete("/{news_id}", response_model=str)
async def delete_news(
    news: News = Depends(get_news_or_404),
    db: Session = Depends(get_db),
    supabase: Client = Depends(get_supabase)
):
    """Delete a news item and its associated image"""
    try:
        if news.image_url:
            await delete_image_from_storage(news.image_url, supabase)

        db.delete(news)
        db.commit()
        return "News item deleted successfully"

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete news item: {str(e)}"
        )

@router.get("/latest", response_model=List[NewsResponse])
def get_latest_news(
    limit: int = Query(5, gt=0, le=20),
    db: Session = Depends(get_db)
):
    """Get latest news articles"""
    try:
        items = db.query(News)\
                 .filter(News.is_published == True)\
                 .order_by(News.created_at.desc())\
                 .limit(limit)\
                 .all()
        return items
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching latest news: {str(e)}"
        )

@router.post("/upload-image", response_model=dict)
async def upload_news_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """Standalone endpoint for image uploads"""
    try:
        image_url = await save_upload_file(file, supabase)
        return {"url": image_url}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )