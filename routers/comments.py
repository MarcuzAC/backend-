from fastapi import APIRouter, Depends, HTTPException, Response, status
from requests import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import UUID, select
from typing import List
import uuid

from database import get_db
from auth import get_current_user
import models
import schemas
import crud
from models import User, Video

router = APIRouter(prefix="/comments", tags=["comments"])

@router.post("/", response_model=schemas.CommentResponse)
async def add_comment(
    comment: schemas.CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)  # This already validates the user
):
    """Add a new comment to a video"""
    # Check if the video exists
    video = await db.get(Video, comment.video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Create and save the comment using the authenticated user's ID
    return await crud.add_comment(db=db, comment=comment, user_id=current_user.id)

@router.get("/{video_id}", response_model=List[schemas.CommentResponse])
async def get_comments(
    video_id: uuid.UUID, 
    db: AsyncSession = Depends(get_db)
):
    """Get all comments for a specific video"""
    # Check if the video exists
    video_exists = await db.scalar(select(Video.id).filter(Video.id == video_id))
    if not video_exists:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return await crud.get_comments(db=db, video_id=video_id)


@router.put("/comments/{comment_id}", response_model=schemas.Comment)
async def update_comment(
    comment_id: UUID,
    updated_data: schemas.CommentUpdate,  # assuming it has a 'text' field
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    comment = db.query(models.Comment).filter(models.Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    comment.text = updated_data.text
    db.commit()
    db.refresh(comment)
    return comment


@router.delete("/comments/{comment_id}", status_code=200)
async def delete_comment(
    comment_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    comment = db.query(models.Comment).filter(models.Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db.delete(comment)
    db.commit()
    return {"detail": "Comment deleted successfully"}
