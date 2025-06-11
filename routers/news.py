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

router = APIRouter(tags=["news"])


# Helper Functions
async def save_upload_file(file: UploadFile, supabase: Client) -> str:
    """Upload file to storage and return URL"""
    try:
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
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}"
        )


# Endpoints
@router.post("/news", response_model=NewsResponse)
async def create_news(
    news_data: str = Form(...),
    db: Session = Depends(get_db),
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


@router.get("/news", response_model=NewsListResponse)
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


@router.get("/news/{news_id}", response_model=NewsResponse)
def get_news(
    news_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Get a single news item by ID"""
    try:
        news = db.query(News).filter(News.id == news_id).first()
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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving news item: {str(e)}"
        )


@router.put("/news/{news_id}", response_model=NewsResponse)
async def update_news(
    news_id: uuid.UUID,
    news_data: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    image: Optional[UploadFile] = File(None),
    supabase: Client = Depends(lambda: settings.supabase)
):
    """Update a news item with optional image update"""
    try:
        try:
            news_update = json.loads(news_data)
            news_update = NewsUpdate(**news_update)
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid news_data format"
            )

        news = db.query(News).filter(News.id == news_id).first()
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


@router.delete("/news/{news_id}", response_model=str)
def delete_news(
    news_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    supabase: Client = Depends(lambda: settings.supabase)
):
    """Delete a news item and its associated image"""
    try:
        news = db.query(News).filter(News.id == news_id).first()
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

        db.delete(news)
        db.commit()
        return "News item deleted successfully"

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid news ID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete news item: {str(e)}"
        )


@router.get("/news/latest", response_model=List[NewsResponse])
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


@router.get("/news/search", response_model=NewsListResponse)
def search_news(
    query: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, gt=0),
    size: int = Query(10, gt=0, le=100),
    published_only: bool = Query(True),
    db: Session = Depends(get_db)
):
    """Search news articles by title or content"""
    try:
        q = db.query(News)
        if published_only:
            q = q.filter(News.is_published == True)
        q = q.filter(
            (News.title.ilike(f"%{query}%")) |
            (News.content.ilike(f"%{query}%"))
        )
        total = q.count()
        items = q.order_by(News.created_at.desc())\
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


@router.post("/news/upload-image", response_model=dict)
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