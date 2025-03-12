from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from auth import get_current_user
import schemas
import crud
import uuid

router = APIRouter(prefix="/categories", tags=["categories"])

@router.post("/", response_model=schemas.CategoryResponse)
async def create_category(
    category: schemas.CategoryCreate,
    db: AsyncSession = Depends(get_db)
):
    existing_category = await crud.get_category_by_name(db, category.name)
    if existing_category:
        raise HTTPException(status_code=400, detail="Category already exists")
    return await crud.create_category(db, category)

@router.put("/{category_id}", response_model=schemas.CategoryResponse)
async def update_category(
    category_id: uuid.UUID,
    category: schemas.CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserResponse = Depends(get_current_user)
):
    db_category = await crud.get_category(db, category_id)
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    return await crud.update_category(db, db_category, category)

@router.delete("/{category_id}")
async def delete_category(
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserResponse = Depends(get_current_user)
):
    category = await crud.get_category(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    await crud.delete_category(db, category)
    return {"message": "Category deleted successfully"}


@router.get("/", response_model=List[schemas.CategoryResponse])
async def read_categories(
    skip: int = 0, 
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    categories = await crud.get_all_categories(db)
    return categories

@router.get("/{category_id}", response_model=schemas.CategoryResponse)
async def read_category(
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    category = await crud.get_category(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category
