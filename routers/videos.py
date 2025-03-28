from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from typing import List, Optional
from database import get_db
from auth import get_current_user
import schemas
import crud
import uuid
import tempfile
import os
from models import User, Video, Category, Like, Comment
from sqlalchemy.orm import joinedload
from vimeo_client import upload_to_vimeo, client

router = APIRouter(prefix="/videos", tags=["videos"])


# Create a new video with thumbnail
@router.post("/", response_model=schemas.VideoResponse)
async def create_video(
    title: str = Form(...),
    category_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    thumbnail: Optional[UploadFile] = File(None),  # Add thumbnail file
    db: AsyncSession = Depends(get_db)
):
    temp_path = None
    thumbnail_path = None
    try:
        # Validate video file type
        if file.content_type not in ["video/mp4", "video/quicktime", "video/x-msvideo"]:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Unsupported file type. Only MP4, MOV, and AVI are allowed."
            )

        # Save video temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name

        # Save thumbnail temp file (if provided)
        if thumbnail:
            if thumbnail.content_type not in ["image/jpeg", "image/png", "image/gif"]:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail="Unsupported thumbnail type. Only JPEG, PNG, and GIF are allowed."
                )
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(thumbnail.filename)[1]) as thumbnail_temp_file:
                thumbnail_content = await thumbnail.read()
                thumbnail_temp_file.write(thumbnail_content)
                thumbnail_path = thumbnail_temp_file.name

        # Upload video to Vimeo
        try:
            vimeo_data = upload_to_vimeo(temp_path, title=title)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload video to Vimeo: {str(e)}"
            )

        # Upload thumbnail to a storage service (e.g., local storage)
        thumbnail_url = None
        if thumbnail_path:
            try:
                # Example: Upload to a local folder
                thumbnail_filename = f"{uuid.uuid4()}{os.path.splitext(thumbnail.filename)[1]}"
                thumbnail_dir = "thumbnails"
                os.makedirs(thumbnail_dir, exist_ok=True)
                thumbnail_url = f"/{thumbnail_dir}/{thumbnail_filename}"
                os.rename(thumbnail_path, os.path.join(thumbnail_dir, thumbnail_filename))
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to upload thumbnail: {str(e)}"
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
                vimeo_id=vimeo_data['vimeo_id'],
                thumbnail_url=thumbnail_url  # Pass thumbnail URL
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save video to database: {str(e)}"
            )

        return schemas.VideoResponse(
            id=db_video.id,
            title=db_video.title,
            created_date=db_video.created_date,
            vimeo_url=db_video.vimeo_url,
            vimeo_id=db_video.vimeo_id,
            category=db_video.category.name if db_video.category else None,
            thumbnail_url=db_video.thumbnail_url  # Include thumbnail URL
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

    finally:
        # Cleanup temp files
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as e:
                print(f"Failed to delete video temp file: {str(e)}")
        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                os.remove(thumbnail_path)
            except Exception as e:
                print(f"Failed to delete thumbnail temp file: {str(e)}")


# Get dashboard stats
@router.get("/dashboard/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Retrieve total users, videos, and categories. Revenue is set to 0 by default."""
    total_users = await db.scalar(func.count(User.id))
    total_videos = await db.scalar(func.count(Video.id))
    total_categories = await db.scalar(func.count(Category.id))

    return {
        "total_users": total_users or 0,
        "total_videos": total_videos or 0,
        "total_categories": total_categories or 0,
        "revenue": 0  # Default to 0
    }


# Get recent videos
@router.get("/recent", response_model=List[schemas.VideoResponse])
async def get_recent_videos(db: AsyncSession = Depends(get_db)):
    """Retrieve the most recent uploaded videos."""
    videos = await crud.get_recent_videos(db)
    return videos


# Update a video
@router.put("/{video_id}", response_model=schemas.VideoResponse)
async def update_video(
    video_id: uuid.UUID,
    video_update: schemas.VideoUpdate,  # Accept JSON request body
    thumbnail: Optional[UploadFile] = File(None),  # Add thumbnail file
    db: AsyncSession = Depends(get_db)
):
    # Fetch video
    result = await db.execute(
        select(Video).options(joinedload(Video.category)).filter(Video.id == video_id)
    )
    video = result.scalars().first()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    update_data = video_update.model_dump(exclude_unset=True)

    if "category_id" in update_data and update_data["category_id"] is not None:
        category_exists = await db.execute(select(Category).filter(Category.id == update_data["category_id"]))
        if not category_exists.scalars().first():
            raise HTTPException(status_code=400, detail="Invalid category_id.")

    # Update thumbnail (if provided)
    if thumbnail:
        if thumbnail.content_type not in ["image/jpeg", "image/png", "image/gif"]:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Unsupported thumbnail type. Only JPEG, PNG, and GIF are allowed."
            )

        # Upload new thumbnail
        try:
            thumbnail_filename = f"{uuid.uuid4()}{os.path.splitext(thumbnail.filename)[1]}"
            thumbnail_dir = "thumbnails"
            os.makedirs(thumbnail_dir, exist_ok=True)
            thumbnail_url = f"/{thumbnail_dir}/{thumbnail_filename}"
            with open(os.path.join(thumbnail_dir, thumbnail_filename), "wb") as buffer:
                buffer.write(await thumbnail.read())
            video.thumbnail_url = thumbnail_url
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload thumbnail: {str(e)}"
            )

    # Apply updates
    for key, value in update_data.items():
        setattr(video, key, value)

    db.add(video)
    await db.commit()
    await db.refresh(video)

    return schemas.VideoResponse(
        id=video.id,
        title=video.title,
        created_date=video.created_date,
        vimeo_url=video.vimeo_url,
        vimeo_id=video.vimeo_id,
        category=video.category.name if video.category else None,
        thumbnail_url=video.thumbnail_url  # Include thumbnail URL
    )


# Delete a video
@router.delete("/{video_id}")
async def delete_video(
    video_id: uuid.UUID, 
    db: AsyncSession = Depends(get_db)
):
    video = await crud.get_video(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Delete from Vimeo
    try:
        response = client.delete(f"/videos/{video.vimeo_id}")
        if response.status_code != 204:
            raise HTTPException(status_code=500, detail=f"Vimeo deletion failed: {response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vimeo deletion failed: {str(e)}")
    
    await crud.delete_video(db, video)
    return {"message": "Video deleted successfully"}


# Get all videos
@router.get("/", response_model=List[schemas.VideoResponse])
async def read_videos(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    videos = await crud.get_all_videos(db, skip=skip, limit=limit)
    return videos


# Get a single video by ID
@router.get("/{video_id}", response_model=schemas.VideoResponse)
async def read_video(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Video)
        .options(joinedload(Video.category), joinedload(Video.likes), joinedload(Video.comments))
        .filter(Video.id == video_id)
    )
    video = result.scalars().first()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    return schemas.VideoResponse(
        id=video.id,
        title=video.title,
        created_date=video.created_date,
        vimeo_url=video.vimeo_url,
        vimeo_id=video.vimeo_id,
        category=video.category.name if video.category else None,
        thumbnail_url=video.thumbnail_url,
        likes=video.likes,  # Include likes
        comments=video.comments  # Include comments
    )