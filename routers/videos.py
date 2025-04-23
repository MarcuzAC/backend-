from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, func, select
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


@router.delete("/{video_id}")
async def delete_video(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserResponse = Depends(get_current_user)
):
    """
    Delete a video and all its associated data (comments, likes) in a transaction.
    Also removes from Vimeo.
    """
    try:
        # Start a transaction
        async with db.begin():
            # 1. Get the video with all relationships
            result = await db.execute(
                select(Video)
                .options(
                    joinedload(Video.comments),
                    joinedload(Video.likes)
                )
                .filter(Video.id == video_id)
            )
            video = result.scalars().first()

            if not video:
                raise HTTPException(status_code=404, detail="Video not found")

            # 2. Delete from Vimeo first
            try:
                if video.vimeo_id:
                    response = client.delete(f"/videos/{video.vimeo_id}")
                    if response.status_code != 204:
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Vimeo deletion failed: {response.text}"
                        )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Vimeo API error: {str(e)}"
                )

            # 3. Delete associated comments
            if video.comments:
                await db.execute(delete(Comment).where(Comment.video_id == video.id))

            # 4. Delete associated likes
            if video.likes:
                await db.execute(delete(Like).where(Like.video_id == video.id))

            # 5. Delete the video itself
            await db.delete(video)

            # 6. Delete thumbnail file if exists
            if video.thumbnail_url and video.thumbnail_url.startswith("/thumbnails/"):
                try:
                    thumbnail_path = os.path.join("thumbnails", os.path.basename(video.thumbnail_url))
                    if os.path.exists(thumbnail_path):
                        os.remove(thumbnail_path)
                except Exception as e:
                    # Log but don't fail the operation
                    print(f"Failed to delete thumbnail: {str(e)}")

        return {"message": "Video deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete video: {str(e)}"
        )

@router.get("/search", response_model=List[schemas.VideoResponse])
async def search_videos(
    query: Optional[str] = None,
    category_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    # Start with base query
    stmt = select(Video).offset(skip).limit(limit)
    
    # Apply search filters
    if query:
        stmt = stmt.where(Video.title.ilike(f"%{query}%"))
    
    if category_id:
        stmt = stmt.where(Video.category_id == category_id)
    
    # Execute query
    result = await db.execute(stmt)
    videos = result.scalars().all()
    
    return videos
@router.get("/", response_model=List[schemas.VideoResponse])
async def read_videos(
    skip: int = 0,
    limit: int = 100,
    category_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(Video).offset(skip).limit(limit)
    
    if category_id:
        query = query.where(Video.category_id == category_id)
        
    videos = await crud.get_all_videos(db, skip=skip, limit=limit, category_id=category_id)
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
@router.get("/share/{video_id}", response_class=HTMLResponse)
async def share_video(
    video_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Android-only sharing endpoint with direct MediaFire APK download"""
    # Verify video exists
    video = await crud.get_video(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    user_agent = request.headers.get("user-agent", "").lower()
    
    # Android detection
    is_android = "android" in user_agent
    
    # MediaFire APK download link
    apk_download_url = "https://www.mediafire.com/file/p4bfs7dc7x78ivz/mcltv.apk/file"
    
    # HTML response that tries to open app first, then redirects to MediaFire
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta property="og:title" content="{video.title}">
        <meta property="og:description" content="Watch this video in MCL TV app.">
        <meta property="og:image" content="{request.base_url}{video.thumbnail_url.lstrip('/')}">
        <meta property="og:url" content="{request.url}">
        <script>
            function redirectToApp() {{
                // Try to open the Android app
                window.location.href = 'mlctv://video/{video_id}';
                
                // If app not installed, redirect to MediaFire after timeout
                setTimeout(function() {{
                    window.location.href = '{apk_download_url}';
                }}, 500);
            }}
            
            // Only attempt redirect if on Android
            {"window.onload = redirectToApp;" if is_android else ""}
        </script>
    </head>
    <body>
        <div style="text-align: center; padding: 50px;">
            <h1>{video.title}</h1>
            {"<p>For the best experience, please install our Android app.</p>" if is_android else "<p>This content is available on Android devices only.</p>"}
            {"<a href='{apk_download_url}'><button style='padding: 10px 20px; background-color: #4285F4; color: white; border: none; border-radius: 5px; font-size: 16px;'>Download Android App</button></a>" if is_android else ""}
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)