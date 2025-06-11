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
    Query,
    status,
    UploadFile
)
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
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

# Constants
SUPPORTED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif"
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Helper Functions
async def save_upload_file(file: UploadFile, supabase: Client) -> str:
    """Upload file to storage and return URL"""
    try:
        # Validate file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset pointer
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Max size is {MAX_FILE_SIZE/1024/1024}MB"
            )

        # Validate content type
        if file.content_type not in SUPPORTED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported file type. Allowed: {', '.join(SUPPORTED_IMAGE_TYPES.keys())}"
            )

        file_ext = SUPPORTED_IMAGE_TYPES[file.content_type]
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

# Endpoints
@router.post("/", response_model=NewsResponse)
async def create_news(
    news_data: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    image: Optional[UploadFile] = File(None),
    supabase: Client = Depends(lambda: settings.supabase)
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
            author_id=current_user.id,
            created_at=datetime.utcnow()
        )
        
        db.add(db_news)
        await db.commit()
        await db.refresh(db_news)
        return db_news
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create news: {str(e)}"
        )

@router.get("/", response_model=NewsListResponse)
async def get_news_list(
    page: int = Query(1, gt=0),
    size: int = Query(10, gt=0, le=100),
    published_only: bool = Query(True),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated list of news items"""
    try:
        query = select(News)
        
        if published_only:
            query = query.where(News.is_published == True)
        
        # Get total count
        total_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(total_query)
        total = total_result.scalar_one()
        
        # Get paginated items
        items_query = query.order_by(News.created_at.desc())\
                          .offset((page - 1) * size)\
                          .limit(size)
        items_result = await db.execute(items_query)
        items = items_result.scalars().all()
        
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

@router.get("/{news_id}", response_model=NewsResponse)
async def get_news(
    news_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a single news item by ID"""
    try:
        result = await db.execute(
            select(News).where(News.id == news_id)
        )
        news = result.scalars().first()
        
        if not news:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="News item not found"
            )
            
        return news
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid news ID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving news item: {str(e)}"
        )

@router.put("/{news_id}", response_model=NewsResponse)
async def update_news(
    news_id: uuid.UUID,
    news_data: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    image: Optional[UploadFile] = File(None),
    supabase: Client = Depends(lambda: settings.supabase)
):
    """Update a news item with optional image update"""
    try:
        try:
            news_dict = json.loads(news_data)
            news_update = NewsUpdate(**news_dict)
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid news_data format"
            )

        result = await db.execute(
            select(News).where(News.id == news_id)
        )
        news = result.scalars().first()
        
        if not news:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="News item not found"
            )

        if news.author_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this news item"
            )

        if image:
            if news.image_url:
                try:
                    old_filename = news.image_url.split('/')[-1]
                    supabase.storage.from_(settings.SUPABASE_BUCKET).remove([old_filename])
                except Exception as e:
                    print(f"Failed to delete old image: {str(e)}")
            
            news.image_url = await save_upload_file(image, supabase)

        if news_update.title is not None:
            news.title = news_update.title
        if news_update.content is not None:
            news.content = news_update.content
        if news_update.is_published is not None:
            news.is_published = news_update.is_published
        
        news.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(news)
        return news

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update news item: {str(e)}"
        )

@router.delete("/{news_id}")
async def delete_news(
    news_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    supabase: Client = Depends(lambda: settings.supabase)
):
    """Delete a news item and its associated image"""
    try:
        result = await db.execute(
            select(News).where(News.id == news_id)
        )
        news = result.scalars().first()
        
        if not news:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="News item not found"
            )

        if news.author_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this news item"
            )

        if news.image_url:
            try:
                filename = news.image_url.split('/')[-1]
                supabase.storage.from_(settings.SUPABASE_BUCKET).remove([filename])
            except Exception as e:
                print(f"Failed to delete image: {str(e)}")

        await db.delete(news)
        await db.commit()
        return JSONResponse(
            status_code=status.HTTP_204_NO_CONTENT,
            content=None
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid news ID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete news item: {str(e)}"
        )

@router.get("/latest/", response_model=List[NewsResponse])
async def get_latest_news(
    limit: int = Query(5, gt=0, le=20),
    db: AsyncSession = Depends(get_db)
):
    """Get latest news articles"""
    try:
        result = await db.execute(
            select(News)
            .where(News.is_published == True)
            .order_by(News.created_at.desc())
            .limit(limit)
        )
        items = result.scalars().all()
        return items
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching latest news: {str(e)}"
        )

@router.get("/search/", response_model=NewsListResponse)
async def search_news(
    query: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, gt=0),
    size: int = Query(10, gt=0, le=100),
    published_only: bool = Query(True),
    db: AsyncSession = Depends(get_db)
):
    """Search news articles by title or content"""
    try:
        q = select(News)
        if published_only:
            q = q.where(News.is_published == True)
        q = q.where(
            (News.title.ilike(f"%{query}%")) |
            (News.content.ilike(f"%{query}%"))
        )
        
        # Get total count
        total_query = select(func.count()).select_from(q.subquery())
        total_result = await db.execute(total_query)
        total = total_result.scalar_one()
        
        # Get paginated items
        items_query = q.order_by(News.created_at.desc())\
                      .offset((page - 1) * size)\
                      .limit(size)
        items_result = await db.execute(items_query)
        items = items_result.scalars().all()
        
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

@router.post("/upload-image/", response_model=dict)
async def upload_news_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    supabase: Client = Depends(lambda: settings.supabase)
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