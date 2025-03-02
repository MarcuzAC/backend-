from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from auth import get_current_user
import schemas
import crud
import uuid

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/", response_model=List[schemas.UserResponse])
async def read_users(
    skip: int = 0, 
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserResponse = Depends(get_current_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    users = await crud.get_all_users(db)
    return users

@router.get("/{user_id}", response_model=schemas.UserResponse)
async def read_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserResponse = Depends(get_current_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    user = await crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
@router.get("/me", response_model=schemas.UserResponse)
async def read_current_user(current_user: schemas.UserResponse = Depends(get_current_user)):
    return current_user

@router.put("/me", response_model=schemas.UserResponse)
async def update_self(
    user_update: schemas.UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserResponse = Depends(get_current_user)
):
    return await crud.update_user(db, current_user, user_update)

@router.delete("/me")
async def delete_self(
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserResponse = Depends(get_current_user)
):
    await crud.delete_user(db, current_user)
    return {"message": "User deleted successfully"}