from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

import crud
from database import get_db
from schemas import (
    VideoSearchRequest,
    VideoSearchResult,
    SearchSuggestion,
    PopularSearches
)

router = APIRouter(prefix="/videos", tags=["videos"])

@router.get("/search", response_model=list[VideoSearchResult])
async def search_videos_endpoint(
    query: Optional[str] = Query(
        None,
        min_length=1,
        max_length=100,
        description="Text to search in video titles",
        example="tutorial"
    ),
    category_id: Optional[uuid.UUID] = Query(
        None,
        description="Filter by category ID",
        example="a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8"
    ),
    page: int = Query(
        1,
        ge=1,
        description="Page number for pagination",
        example=1
    ),
    limit: int = Query(
        10,
        ge=1,
        le=100,
        description="Items per page",
        example=10
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    Search videos by title and/or category with pagination
    
    Returns:
    - List of videos matching search criteria
    - Includes metadata like like_count and comment_count
    """
    try:
        # Convert to VideoSearchRequest for validation
        search_params = VideoSearchRequest(
            query=query,
            category_id=category_id,
            page=page,
            limit=limit
        )
        
        skip = (search_params.page - 1) * search_params.limit
        videos = await crud.search_videos(
            db,
            query=search_params.query,
            category_id=search_params.category_id,
            skip=skip,
            limit=search_params.limit
        )
        return videos
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Internal server error during search"
        )

@router.get("/suggestions", response_model=SearchSuggestion)
async def get_suggestions(
    query: str = Query(
        ...,
        min_length=1,
        max_length=50,
        description="Partial search term for suggestions",
        example="tut"
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    Get autocomplete suggestions for video search
    
    Returns:
    - List of suggested video titles matching partial input
    """
    try:
        suggestions = await crud.get_video_suggestions(db, query)
        return SearchSuggestion(suggestions=suggestions)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch suggestions"
        )

@router.get("/popular-searches", response_model=PopularSearches)
async def get_popular_searches(
    limit: int = Query(
        5,
        ge=1,
        le=20,
        description="Number of popular terms to return",
        example=5
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    Get most popular search terms
    
    Returns:
    - List of currently trending search terms
    - Ordered by popularity (most searched first)
    """
    try:
        terms = await crud.get_popular_search_terms(db, limit=limit)
        return PopularSearches(terms=terms)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch popular searches"
        )