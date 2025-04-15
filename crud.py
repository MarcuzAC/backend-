from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
import models
import schemas
import uuid
from security import get_password_hash
from sqlalchemy.orm import joinedload

# Fetch all users
async def get_all_users_except_me(db: AsyncSession, my_user_id: uuid.UUID, limit: int):
    result = await db.execute(select(models.User).filter(models.User.id != my_user_id).limit(limit))
    return result.scalars().all()

# Fetch a single user by ID
async def get_user(db: AsyncSession, user_id: uuid.UUID):
    result = await db.execute(select(models.User).filter(models.User.id == user_id))
    return result.scalars().first()

# Fetch all categories
async def get_all_categories(db: AsyncSession):
    result = await db.execute(select(models.Category))
    return result.scalars().all()

# Fetch a single category by ID
async def get_category(db: AsyncSession, category_id: uuid.UUID):
    result = await db.execute(select(models.Category).filter(models.Category.id == category_id))
    return result.scalars().first()

# Fetch all videos
async def get_all_videos(db: AsyncSession, skip: int = 0, limit: int = 100):
    """Fetch all videos with category names included"""
    result = await db.execute(
        select(models.Video.id, models.Video.title, models.Video.created_date, 
               models.Video.vimeo_url, models.Video.vimeo_id, models.Video.thumbnail_url, models.Category.name.label("category"))  # Extract category.name
        .join(models.Category, models.Video.category_id == models.Category.id)
        .offset(skip)
        .limit(limit)
    )

    videos = result.all()
    
    # Convert result into a list of dictionaries
    return [
        {
            "id": v.id,
            "title": v.title,
            "created_date": v.created_date,
            "vimeo_url": v.vimeo_url,
            "vimeo_id": v.vimeo_id,
            "thumbnail_url": v.thumbnail_url,  # Include thumbnail URL
            "category": v.category,  # Now it's a string
            "like_count": await get_like_count(db, v.id),  # Add like count
            "comment_count": await get_comment_count(db, v.id),  # Add comment count
        }
        for v in videos
    ]

# Fetch a user by username
async def get_user_by_username(db: AsyncSession, username: str):
    result = await db.execute(select(models.User).filter(models.User.username == username))
    return result.scalars().first()

# Update user details
async def update_user(db: AsyncSession, user, user_update: schemas.UserUpdate):
    for key, value in user_update.dict(exclude_unset=True).items():
        setattr(user, key, value)
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

# Delete user
async def delete_user(db: AsyncSession, user):
    await db.delete(user)
    await db.commit()

# Create a new video entry
async def create_video(db: AsyncSession, video: schemas.VideoCreate, vimeo_url: str, vimeo_id: str, thumbnail_url: Optional[str] = None):
    db_video = models.Video(
        **video.dict(),
        vimeo_url=vimeo_url,
        vimeo_id=vimeo_id,
        thumbnail_url=thumbnail_url  # Add thumbnail URL
    )
    db.add(db_video)
    await db.commit()
    await db.refresh(db_video)

    # ✅ Fetch the video again with eager-loaded relationships
    result = await db.execute(
        select(models.Video).options(joinedload(models.Video.category)).filter(models.Video.id == db_video.id)
    )
    return result.scalars().first()

# Fetch a video by ID
async def get_video(db: AsyncSession, video_id: uuid.UUID):
    result = await db.execute(
        select(models.Video).options(joinedload(models.Video.category)).filter(models.Video.id == video_id)
    )
    return result.scalars().first()

# Update a video entry
async def update_video(db: AsyncSession, db_video: models.Video, video_update: schemas.VideoUpdate):
    update_data = video_update.model_dump(exclude_unset=True)  # Exclude fields that are not provided

    # Only update title and category_id
    allowed_fields = {"title", "category_id", "thumbnail_url"}  # Add thumbnail_url
    update_data = {key: value for key, value in update_data.items() if key in allowed_fields}

    if not update_data:  # Prevent empty updates
        return db_video

    for key, value in update_data.items():
        setattr(db_video, key, value)

    db.add(db_video)
    await db.commit()
    await db.refresh(db_video)

    return db_video

# Delete a video
async def delete_video(db: AsyncSession, video: models.Video):
    await db.delete(video)
    await db.commit()

# Create a new category
async def create_category(db: AsyncSession, category: schemas.CategoryCreate):
    db_category = models.Category(**category.dict())
    db.add(db_category)
    await db.commit()
    await db.refresh(db_category)
    return db_category

# Fetch category by name
async def get_category_by_name(db: AsyncSession, name: str):
    result = await db.execute(select(models.Category).filter(models.Category.name == name))
    return result.scalars().first()

# Update a category
async def update_category(db: AsyncSession, db_category: models.Category, category_update: schemas.CategoryCreate):
    db_category.name = category_update.name
    await db.commit()
    await db.refresh(db_category)
    return db_category

# Delete a category
async def delete_category(db: AsyncSession, category: models.Category):
    await db.delete(category)
    await db.commit()

# 📌 New Function: Fetch Dashboard Stats
async def get_dashboard_stats(db: AsyncSession):
    """Fetch total users, videos, categories, and revenue (set to 0)."""
    total_users = await db.scalar(func.count(models.User.id))
    total_videos = await db.scalar(func.count(models.Video.id))
    total_categories = await db.scalar(func.count(models.Category.id))

    return {
        "total_users": total_users or 0,
        "total_videos": total_videos or 0,
        "total_categories": total_categories or 0,
        "revenue": 0  # Default revenue
    }

# 📌 New Function: Fetch Recent Videos
async def get_recent_videos(db: AsyncSession):
    """Fetch the most recent uploaded videos with category names."""
    result = await db.execute(
        select(models.Video)
        .options(joinedload(models.Video.category))  # Load category relationship
        .order_by(models.Video.created_date.desc())
        .limit(5)
    )

    videos = result.scalars().all()

    # Format the output to return category name instead of category_id
    return [
        {
            "id": video.id,
            "title": video.title,
            "category": video.category.name if video.category else "Unknown",  # Get category name
            "created_date": video.created_date,
            "vimeo_url": video.vimeo_url,
            "vimeo_id": video.vimeo_id,
            "thumbnail_url": video.thumbnail_url,  # Include thumbnail URL
            "like_count": await get_like_count(db, video.id),  # Add like count
            "comment_count": await get_comment_count(db, video.id),  # Add comment count
        }
        for video in videos
    ]

# 📌 New Function: Add a Like
async def add_like(db: AsyncSession, like: schemas.LikeCreate):
    # Check if the user has already liked the video
    existing_like = await db.execute(
        select(models.Like).filter(models.Like.user_id == like.user_id, models.Like.video_id == like.video_id)
    )
    if existing_like.scalars().first():
        raise ValueError("User has already liked this video")

    # Add the like
    db_like = models.Like(**like.dict())
    db.add(db_like)
    await db.commit()
    await db.refresh(db_like)
    return db_like

# 📌 New Function: Remove a Like
async def remove_like(db: AsyncSession, user_id: uuid.UUID, video_id: uuid.UUID):
    like = await db.execute(
        select(models.Like).filter(models.Like.user_id == user_id, models.Like.video_id == video_id)
    )
    like = like.scalars().first()
    if not like:
        raise ValueError("Like not found")

    await db.delete(like)
    await db.commit()
    return like

# 📌 New Function: Get Like Count for a Video
async def get_like_count(db: AsyncSession, video_id: uuid.UUID):
    result = await db.scalar(
        select(func.count(models.Like.id)).filter(models.Like.video_id == video_id)
    )
    return result or 0


async def add_comment(
    db: AsyncSession, 
    comment: schemas.CommentCreate, 
    user_id: uuid.UUID  # Expect user_id directly instead of token
):
    """Add a comment using the already authenticated user_id"""
    db_comment = models.Comment(
        user_id=user_id,
        video_id=comment.video_id,
        text=comment.text
    )
    db.add(db_comment)
    await db.commit()
    await db.refresh(db_comment)
    return db_comment


# 📌 New Function: Get Comments for a Video
async def get_comments(db: AsyncSession, video_id: uuid.UUID):
    result = await db.execute(
        select(models.Comment)
        .options(joinedload(models.Comment.user))  # Load user relationship
        .filter(models.Comment.video_id == video_id)
        .order_by(models.Comment.created_at.desc())
    )
    return result.scalars().all()

# 📌 New Function: Get Comment Count for a Video
async def get_comment_count(db: AsyncSession, video_id: uuid.UUID):
    result = await db.scalar(
        select(func.count(models.Comment.id)).filter(models.Comment.video_id == video_id)
    )
    return result or 0
async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(models.User).filter(models.User.email == email))
    return result.scalars().first()

# In crud.py

async def update_comment(
    db: AsyncSession,
    comment_id: uuid.UUID,
    text: str
) -> models.Comment:
    """Update a comment's text"""
    comment = await db.get(models.Comment, comment_id)
    if not comment:
        raise ValueError("Comment not found")
    
    comment.text = text
    await db.commit()
    await db.refresh(comment)
    return comment

async def delete_comment(
    db: AsyncSession,
    comment_id: uuid.UUID
) -> None:
    """Delete a comment"""
    comment = await db.get(models.Comment, comment_id)
    if not comment:
        raise ValueError("Comment not found")
    
    await db.delete(comment)
    await db.commit()