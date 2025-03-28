from turtle import update
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, or_, and_
import models
import schemas
import uuid
from security import get_password_hash
from sqlalchemy.orm import joinedload, selectinload

# User Operations
async def get_user(db: AsyncSession, user_id: uuid.UUID) -> Optional[models.User]:
    """Get user by ID with all relationships"""
    result = await db.execute(
        select(models.User)
        .options(selectinload(models.User.likes), selectinload(models.User.comments))
        .filter(models.User.id == user_id)
    )
    return result.scalars().first()

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[models.User]:
    result = await db.execute(select(models.User).filter(models.User.email == email))
    return result.scalars().first()

async def get_user_by_username(db: AsyncSession, username: str) -> Optional[models.User]:
    result = await db.execute(select(models.User).filter(models.User.username == username))
    return result.scalars().first()

async def get_all_users_except_me(db: AsyncSession, my_user_id: uuid.UUID, limit: int = 100) -> List[models.User]:
    result = await db.execute(
        select(models.User)
        .filter(models.User.id != my_user_id)
        .limit(limit)
    )
    return result.scalars().all()

async def create_user(db: AsyncSession, user: schemas.UserCreate) -> models.User:
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        **user.dict(exclude={"password"}),
        hashed_password=hashed_password
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def update_user(db: AsyncSession, user: models.User, user_update: schemas.UserUpdate) -> models.User:
    update_data = user_update.dict(exclude_unset=True)
    if 'password' in update_data:
        update_data['hashed_password'] = get_password_hash(update_data.pop('password'))
    
    for key, value in update_data.items():
        setattr(user, key, value)
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def delete_user(db: AsyncSession, user: models.User) -> None:
    await db.delete(user)
    await db.commit()

# Category Operations
async def get_category(db: AsyncSession, category_id: uuid.UUID) -> Optional[models.Category]:
    result = await db.execute(
        select(models.Category)
        .options(selectinload(models.Category.videos))
        .filter(models.Category.id == category_id)
    )
    return result.scalars().first()

async def get_category_by_name(db: AsyncSession, name: str) -> Optional[models.Category]:
    result = await db.execute(select(models.Category).filter(models.Category.name == name))
    return result.scalars().first()

async def get_all_categories(db: AsyncSession) -> List[models.Category]:
    result = await db.execute(
        select(models.Category)
        .options(selectinload(models.Category.videos))
    )
    return result.scalars().all()

async def create_category(db: AsyncSession, category: schemas.CategoryCreate) -> models.Category:
    db_category = models.Category(**category.dict())
    db.add(db_category)
    await db.commit()
    await db.refresh(db_category)
    return db_category

async def update_category(db: AsyncSession, db_category: models.Category, category_update: schemas.CategoryCreate) -> models.Category:
    db_category.name = category_update.name
    db.add(db_category)
    await db.commit()
    await db.refresh(db_category)
    return db_category

async def delete_category(db: AsyncSession, category: models.Category) -> None:
    await db.delete(category)
    await db.commit()

# Video Operations
async def get_video(db: AsyncSession, video_id: uuid.UUID) -> Optional[models.Video]:
    """Get video with all relationships"""
    result = await db.execute(
        select(models.Video)
        .options(
            joinedload(models.Video.category),
            selectinload(models.Video.likes).joinedload(models.Like.user),
            selectinload(models.Video.comments).joinedload(models.Comment.user)
        )
        .filter(models.Video.id == video_id)
    )
    return result.scalars().first()

async def get_all_videos(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[dict]:
    """Get paginated videos with counts and relationships"""
    result = await db.execute(
        select(
            models.Video,
            func.count(models.Like.id).label('like_count'),
            func.count(models.Comment.id).label('comment_count')
        )
        .join(models.Category, isouter=True)
        .join(models.Like, isouter=True)
        .join(models.Comment, isouter=True)
        .group_by(models.Video.id, models.Category.name)
        .order_by(models.Video.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    
    return [
        {
            "id": video.id,
            "title": video.title,
            "description": video.description,
            "created_date": video.created_at,
            "vimeo_url": video.vimeo_url,
            "vimeo_id": video.vimeo_id,
            "thumbnail_url": video.thumbnail_url,
            "category": video.category.name if video.category else None,
            "like_count": like_count,
            "comment_count": comment_count,
            "view_count": video.view_count
        }
        for video, like_count, comment_count in result.all()
    ]

async def create_video(db: AsyncSession, video: schemas.VideoCreate, vimeo_url: str, vimeo_id: str, thumbnail_url: Optional[str] = None) -> models.Video:
    db_video = models.Video(
        **video.dict(),
        vimeo_url=vimeo_url,
        vimeo_id=vimeo_id,
        thumbnail_url=thumbnail_url
    )
    db.add(db_video)
    await db.commit()
    await db.refresh(db_video)
    return db_video

async def update_video(db: AsyncSession, db_video: models.Video, video_update: schemas.VideoUpdate) -> models.Video:
    update_data = video_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_video, key, value)
    
    db.add(db_video)
    await db.commit()
    await db.refresh(db_video)
    return db_video

async def delete_video(db: AsyncSession, video: models.Video) -> None:
    await db.delete(video)
    await db.commit()

async def increment_video_views(db: AsyncSession, video_id: uuid.UUID) -> None:
    await db.execute(
        update(models.Video)
        .where(models.Video.id == video_id)
        .values(view_count=models.Video.view_count + 1)
    )
    await db.commit()

# Dashboard Operations
async def get_dashboard_stats(db: AsyncSession) -> dict:
    """Get comprehensive dashboard statistics"""
    total_users = await db.scalar(select(func.count(models.User.id)))
    total_videos = await db.scalar(select(func.count(models.Video.id)))
    total_categories = await db.scalar(select(func.count(models.Category.id)))
    total_likes = await db.scalar(select(func.count(models.Like.id)))
    total_comments = await db.scalar(select(func.count(models.Comment.id)))

    return {
        "total_users": total_users or 0,
        "total_videos": total_videos or 0,
        "total_categories": total_categories or 0,
        "total_likes": total_likes or 0,
        "total_comments": total_comments or 0,
        "revenue": 0
    }

async def get_recent_videos(db: AsyncSession, limit: int = 5) -> List[dict]:
    """Get recent videos with counts"""
    result = await db.execute(
        select(
            models.Video,
            func.count(models.Like.id).label('like_count'),
            func.count(models.Comment.id).label('comment_count')
        )
        .join(models.Category, isouter=True)
        .join(models.Like, isouter=True)
        .join(models.Comment, isouter=True)
        .group_by(models.Video.id, models.Category.name)
        .order_by(models.Video.created_at.desc())
        .limit(limit)
    )
    
    return [
        {
            "id": video.id,
            "title": video.title,
            "category": video.category.name if video.category else None,
            "created_date": video.created_at,
            "vimeo_url": video.vimeo_url,
            "thumbnail_url": video.thumbnail_url,
            "like_count": like_count,
            "comment_count": comment_count
        }
        for video, like_count, comment_count in result.all()
    ]

# Like Operations
async def add_like(db: AsyncSession, user_id: uuid.UUID, video_id: uuid.UUID) -> models.Like:
    # Check for existing like
    existing_like = await db.execute(
        select(models.Like)
        .filter(and_(
            models.Like.user_id == user_id,
            models.Like.video_id == video_id
        ))
    )
    if existing_like.scalars().first():
        raise ValueError("User already liked this video")

    db_like = models.Like(user_id=user_id, video_id=video_id)
    db.add(db_like)
    await db.commit()
    await db.refresh(db_like)
    return db_like

async def remove_like(db: AsyncSession, user_id: uuid.UUID, video_id: uuid.UUID) -> Optional[models.Like]:
    result = await db.execute(
        select(models.Like)
        .filter(and_(
            models.Like.user_id == user_id,
            models.Like.video_id == video_id
        ))
    )
    like = result.scalars().first()
    if like:
        await db.delete(like)
        await db.commit()
    return like

async def get_like_count(db: AsyncSession, video_id: uuid.UUID) -> int:
    result = await db.scalar(
        select(func.count(models.Like.id))
        .filter(models.Like.video_id == video_id)
    )
    return result or 0

async def check_user_like(db: AsyncSession, user_id: uuid.UUID, video_id: uuid.UUID) -> bool:
    result = await db.scalar(
        select(models.Like.id)
        .filter(and_(
            models.Like.user_id == user_id,
            models.Like.video_id == video_id
        ))
    )
    return result is not None

# Comment Operations
async def add_comment(db: AsyncSession, user_id: uuid.UUID, video_id: uuid.UUID, content: str) -> models.Comment:
    db_comment = models.Comment(
        user_id=user_id,
        video_id=video_id,
        content=content
    )
    db.add(db_comment)
    await db.commit()
    await db.refresh(db_comment)
    return db_comment

async def get_comments(db: AsyncSession, video_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[models.Comment]:
    result = await db.execute(
        select(models.Comment)
        .options(joinedload(models.Comment.user))
        .filter(models.Comment.video_id == video_id)
        .order_by(models.Comment.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().unique().all()

async def get_comment_count(db: AsyncSession, video_id: uuid.UUID) -> int:
    result = await db.scalar(
        select(func.count(models.Comment.id))
        .filter(models.Comment.video_id == video_id)
    )
    return result or 0

async def delete_comment(db: AsyncSession, comment_id: uuid.UUID) -> Optional[models.Comment]:
    result = await db.execute(
        select(models.Comment)
        .filter(models.Comment.id == comment_id)
    )
    comment = result.scalars().first()
    if comment:
        await db.delete(comment)
        await db.commit()
    return comment