from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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

@router.put("/{comment_id}", response_model=schemas.CommentResponse)
async def update_comment(
    comment_id: uuid.UUID,
    comment_update: schemas.CommentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an existing comment"""
    # Get the comment from database
    comment = await db.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Verify the comment belongs to the current user
    if comment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own comments"
        )
    
    # Update the comment
    return await crud.update_comment(
        db=db, 
        comment_id=comment_id,
        text=comment_update.text
    )

@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a comment"""
    # Get the comment from database
    comment = await db.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Verify the comment belongs to the current user
    if comment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own comments"
        )
    
    # Delete the comment
    await crud.delete_comment(db=db, comment_id=comment_id)
    return None