
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
import uuid
from database import get_db
from auth import get_current_user
import schemas
import crud
from models import User, Video, Comment

router = APIRouter(prefix="/comments", tags=["comments"])

@router.post("/", response_model=schemas.CommentResponse)
async def add_comment(
    comment: schemas.CommentCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a new comment to a video"""
    # Verify video exists
    video = await db.get(Video, comment.video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return await crud.add_comment(db=db, comment=comment, user_id=current_user.id)

@router.get("/{video_id}", response_model=List[schemas.CommentResponse])
async def get_comments(
    video_id: uuid.UUID, 
    db: AsyncSession = Depends(get_db)
):
    """Get all comments for a specific video"""
    # Verify video exists
    video_exists = await db.scalar(select(Video.id).filter(Video.id == video_id))
    if not video_exists:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return await crud.get_comments(db=db, video_id=video_id)