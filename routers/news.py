from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import os
from datetime import datetime
from config import settings
from supabase import Client

# Import your existing components
from database import get_db
from models import News, User
from schemas import NewsCreate, NewsUpdate, NewsResponse, NewsListResponse
from auth import get_current_user

router = APIRouter(prefix="/news", tags=["news"])

async def save_upload_file(file: UploadFile, supabase: Client) -> str:
    """Upload file to storage and return URL"""
    try:
        # Generate unique filename
        file_ext = os.path.splitext(file.filename)[1]
        file_name = f"{uuid.uuid4()}{file_ext}"
        
        # Using Supabase Storage
        contents = await file.read()
        res = supabase.storage.from_(settings.SUPABASE_BUCKET).upload(
            file=contents,
            path=file_name,
            file_options={"content-type": file.content_type}
        )
        
        # Get public URL
        url = supabase.storage.from_(settings.SUPABASE_BUCKET).get_public_url(file_name)
        return url
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}"
        )

@router.post("/", response_model=NewsResponse)
async def create_news(
    news_data: NewsCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    image: Optional[UploadFile] = File(None),
    supabase: Client = Depends(lambda: settings.supabase)
):
    """Create a new news article with optional image"""
    try:
        # Handle image upload if provided
        image_url = None
        if image:
            image_url = await save_upload_file(image, supabase)
        
        # Create news item
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
    page: int = 1,
    size: int = 10,
    published_only: bool = True,
    db: Session = Depends(get_db)
):
    """Get paginated list of news articles"""
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

@router.get("/{news_id}", response_model=NewsResponse)
def get_news(
    news_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Get a single news article by ID"""
    news = db.query(News).filter(News.id == news_id).first()
    if not news:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="News not found"
        )
    return news

@router.put("/{news_id}", response_model=NewsResponse)
async def update_news(
    news_id: uuid.UUID,
    news_data: NewsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    image: Optional[UploadFile] = File(None),
    supabase: Client = Depends(lambda: settings.supabase)
):
    """Update a news article with optional new image"""
    news = db.query(News).filter(News.id == news_id).first()
    if not news:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="News not found"
        )
    
    # Verify ownership or admin status
    if news.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this news"
        )
    
    try:
        # Handle image upload if provided
        if image:
            news.image_url = await save_upload_file(image, supabase)
        
        # Update other fields
        if news_data.title is not None:
            news.title = news_data.title
        if news_data.content is not None:
            news.content = news_data.content
        if news_data.is_published is not None:
            news.is_published = news_data.is_published
        
        news.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(news)
        
        return news
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/{news_id}")
def delete_news(
    news_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a news article"""
    news = db.query(News).filter(News.id == news_id).first()
    if not news:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="News not found"
        )
    
    # Verify ownership or admin status
    if news.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this news"
        )
    
    try:
        db.delete(news)
        db.commit()
        return {"message": "News deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/upload-image", response_model=dict)
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