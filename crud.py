from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import models
import schemas
import uuid
from security import get_password_hash

async def get_all_users(db: AsyncSession):
    result = await db.execute(select(models.User))
    return result.scalars().all()

async def get_user(db: AsyncSession, user_id: uuid.UUID):
    result = await db.execute(select(models.User).filter(models.User.id == user_id))
    return result.scalars().first()

async def get_all_categories(db: AsyncSession):
    result = await db.execute(select(models.Category))
    return result.scalars().all()

async def get_category(db: AsyncSession, category_id: uuid.UUID):
    result = await db.execute(select(models.Category).filter(models.Category.id == category_id))
    return result.scalars().first()

async def get_all_videos(db: AsyncSession):
    result = await db.execute(select(models.Video))
    return result.scalars().all()
async def get_user_by_username(db: AsyncSession, username: str):
    result = await db.execute(select(models.User).filter(models.User.username == username))
    return result.scalars().first()

async def update_user(db: AsyncSession, user: models.User, user_update: schemas.UserUpdate):
    update_data = user_update.dict(exclude_unset=True)
    if "password" in update_data:
        hashed_password = get_password_hash(update_data["password"])
        del update_data["password"]
        update_data["hashed_password"] = hashed_password
    
    for key, value in update_data.items():
        setattr(user, key, value)
    
    await db.commit()
    await db.refresh(user)
    return user

async def delete_user(db: AsyncSession, user: models.User):
    await db.delete(user)
    await db.commit()

async def create_video(db: AsyncSession, video: schemas.VideoCreate, vimeo_url: str, vimeo_id: str):
    db_video = models.Video(
        **video.dict(),
        vimeo_url=vimeo_url,
        vimeo_id=vimeo_id
    )
    db.add(db_video)
    await db.commit()
    await db.refresh(db_video)
    return db_video

async def get_video(db: AsyncSession, video_id: uuid.UUID):
    result = await db.execute(select(models.Video).filter(models.Video.id == video_id))
    return result.scalars().first()

async def update_video(db: AsyncSession, db_video: models.Video, video_update: schemas.VideoCreate):
    for key, value in video_update.dict().items():
        setattr(db_video, key, value)
    await db.commit()
    await db.refresh(db_video)
    return db_video

async def delete_video(db: AsyncSession, video: models.Video):
    await db.delete(video)
    await db.commit()

async def create_category(db: AsyncSession, category: schemas.CategoryCreate):
    db_category = models.Category(**category.dict())
    db.add(db_category)
    await db.commit()
    await db.refresh(db_category)
    return db_category


# Add this function to crud.py
async def get_category_by_name(db: AsyncSession, name: str):
    result = await db.execute(select(models.Category).filter(models.Category.name == name))
    return result.scalars().first()

async def update_category(db: AsyncSession, db_category: models.Category, category_update: schemas.CategoryCreate):
    db_category.name = category_update.name
    await db.commit()
    await db.refresh(db_category)
    return db_category

async def delete_category(db: AsyncSession, category: models.Category):
    await db.delete(category)
    await db.commit()