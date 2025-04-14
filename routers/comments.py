from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid
from datetime import datetime

from database import get_db
from auth import get_current_user
import schemas
import crud
from models import User, Video

router = APIRouter(
    prefix="/comments",
    tags=["comments"],
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Resource not found"},
        status.HTTP_403_FORBIDDEN: {"description": "Operation forbidden"}
    }
)

@router.post(
    "/",
    response_model=schemas.CommentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Video not found"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid input"}
    }
)
async def add_comment(
    comment: schemas.CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> schemas.CommentResponse:
    """
    Add a new comment to a video
    
    - **video_id**: UUID of the video to comment on (required)
    - **text**: Comment content (required, max 500 characters)
    """
    try:
        # Check if the video exists
        video = await db.get(Video, comment.video_id)
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        # Validate comment text length
        if len(comment.text.strip()) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Comment text cannot be empty"
            )
        
        if len(comment.text) > 500:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Comment cannot exceed 500 characters"
            )
        
        # Create and save the comment
        db_comment = await crud.add_comment(
            db=db,
            video_id=comment.video_id,
            text=comment.text.strip(),
            user_id=current_user.id
        )
        
        return db_comment
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get(
    "/{video_id}",
    response_model=List[schemas.CommentResponse],
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Video not found"}
    }
)
async def get_comments(
    video_id: uuid.UUID, 
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
) -> List[schemas.CommentResponse]:
    """
    Get all comments for a specific video
    
    - **video_id**: UUID of the video to get comments for
    - **skip**: Number of comments to skip (default 0)
    - **limit**: Maximum number of comments to return (default 100)
    """
    # Check if the video exists
    video_exists = await db.scalar(
        select(Video.id).filter(Video.id == video_id)
    )
    if not video_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    comments = await crud.get_comments(
        db=db,
        video_id=video_id,
        skip=skip,
        limit=limit
    )
    
    return comments