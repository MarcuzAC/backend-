from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid
from database import get_db
import schemas
import crud

router = APIRouter(prefix="/comments", tags=["comments"])

# Add a comment
@router.post("/", response_model=schemas.CommentResponse)
async def add_comment(comment: schemas.CommentCreate, db: AsyncSession = Depends(get_db)):
    return await crud.add_comment(db, comment)

# Fetch comments for a video
@router.get("/{video_id}", response_model=List[schemas.CommentResponse])
async def get_comments(video_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await crud.get_comments(db, video_id)