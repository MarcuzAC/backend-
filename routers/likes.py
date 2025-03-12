from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid
from database import get_db
import schemas
import crud

router = APIRouter(prefix="/likes", tags=["likes"])

# Add a like
@router.post("/", response_model=schemas.LikeResponse)
async def add_like(like: schemas.LikeCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await crud.add_like(db, like)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Remove a like
@router.delete("/", response_model=schemas.LikeResponse)
async def remove_like(user_id: uuid.UUID, video_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await crud.remove_like(db, user_id, video_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# Get like count for a video
@router.get("/{video_id}/count", response_model=int)
async def get_like_count(video_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await crud.get_like_count(db, video_id)
