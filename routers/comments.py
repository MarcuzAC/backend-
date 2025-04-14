from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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
async def create_comment(
    comment_data: schemas.CommentCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        return await crud.add_comment(
            db=db,
            video_id=comment_data.video_id,
            user_id=current_user.id,
            text=comment_data.text
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create comment")

@router.get("/{video_id}", response_model=list[schemas.CommentResponse])
async def read_comments(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    try:
        return await crud.get_comments(db, video_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch comments")