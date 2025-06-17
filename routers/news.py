import json
from datetime import datetime
from typing import List, Optional
import uuid

from fastapi import (
    APIRouter, 
    Depends, 
    HTTPException, 
    Query,
    UploadFile,
    File,
    status,
)
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

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
from utils import upload_news_image

router = APIRouter(prefix="", tags=["news"])

@router.post("/", response_model=NewsResponse)
async def create_news(
    news_data: NewsCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new news article"""
    try:
        db_news = News(
            title=news_data.title,
            content=news_data.content,
            image_url=news_data.image_url,
            is_published=news_data.is_published,
            author_id=current_user.id,
            created_at=datetime.utcnow()
        )
        
        db.add(db_news)
        await db.commit()
        await db.refresh(db_news)
        return db_news
        
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
    news_data: NewsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a news item"""
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
                detail="Not authorized to update this news item"
            )

        if news_data.title is not None:
            news.title = news_data.title
        if news_data.content is not None:
            news.content = news_data.content
        if news_data.image_url is not None:
            news.image_url = news_data.image_url
        if news_data.is_published is not None:
            news.is_published = news_data.is_published
        
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
):
    """Delete a news item"""
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
# Add to your news.py router
@router.post("/upload-news-image")
async def upload_news_image_endpoint(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Endpoint for uploading news images"""
    try:
        image_url = await upload_news_image(file)
        return {"url": image_url}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process image upload: {str(e)}"
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
