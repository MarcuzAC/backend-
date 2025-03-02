from http import client
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from database import get_db
from auth import get_current_user
import schemas
import crud
import uuid
import tempfile
import os
from vimeo_client import upload_to_vimeo

router = APIRouter(prefix="/videos", tags=["videos"])

@router.post("/", response_model=schemas.VideoResponse)
async def create_video(
    title: str = Form(...),
    category_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    temp_path = None
    try:
        # Validate file type
        if file.content_type not in ["video/mp4", "video/quicktime", "video/x-msvideo"]:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Unsupported file type. Only MP4, MOV, and AVI are allowed."
            )

        # Save temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name

        # Upload to Vimeo
        try:
            vimeo_data = upload_to_vimeo(temp_path, title=title)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload video to Vimeo: {str(e)}"
            )

        # Create video entry
        video_data = schemas.VideoCreate(
            title=title,
            category_id=category_id
        )
        
        # Save to database
        try:
            db_video = await crud.create_video(
                db=db,
                video=video_data,
                vimeo_url=vimeo_data['vimeo_url'],
                vimeo_id=vimeo_data['vimeo_id']
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save video to database: {str(e)}"
            )
        
        return db_video

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

    finally:
        # Cleanup temp file
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as e:
                print(f"Failed to delete temp file: {str(e)}")
@router.put("/{video_id}", response_model=schemas.VideoResponse)
async def update_video(
    video_id: uuid.UUID,
    title: str = Form(None),
    category_id: uuid.UUID = Form(None),
    file: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserResponse = Depends(get_current_user)
):
    video = await crud.get_video(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if title:
        video.title = title
    if category_id:
        video.category_id = category_id
    
    if file:
        os.remove(video.video)
        file_path = f"videos/{uuid.uuid4()}_{file.filename}"
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        video.video = file_path
    
    await db.commit()
    await db.refresh(video)
    return video

@router.delete("/{video_id}")
async def delete_video(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserResponse = Depends(get_current_user)
):
    video = await crud.get_video(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Delete from Vimeo
    try:
        client.delete(f"/videos/{video.vimeo_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vimeo deletion failed: {str(e)}")
    
    await crud.delete_video(db, video)
    return {"message": "Video deleted successfully"}

@router.get("/", response_model=List[schemas.VideoResponse])
async def read_videos(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    videos = await crud.get_all_videos(db)
    return videos

@router.get("/{video_id}", response_model=schemas.VideoResponse)
async def read_video(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    video = await crud.get_video(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video