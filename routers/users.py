from fastapi import FastAPI, Request, HTTPException, status, Depends, APIRouter
from typing import Annotated
from sqlalchemy import select
from datetime import timedelta
from auth import create_access_token,hash_password, oauth2_scheme, verify_password, verify_access_token
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import selectinload
from config import settings
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from schemas import UserCreate, UserPrivate, UserPublic, PostResponse, Token, UserUpdate
import model
from database import Base, engine, get_db
router = APIRouter()

@router.post(
    "",
    response_model=UserPrivate,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(model.User).where(func.lower(model.User.username) == user.username.lower()),
    )

    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user already exit",
        )
    
    
    result = await db.execute(
        select(model.User).where(model.User.email == user.email)
    )

    existing_email = result.scalars().first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
             detail="email already exit",
        )
    
    new_user = model.User(
        username=user.username,
        email=user.email.lower(),
        password_hash=hash_password(user.password),
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

"""login for access token"""
@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Annotated[AsyncSession, Depends(get_db)]):

    # Look up user by email (case-insensitive)
    # Note: OAuth2PasswordRequestForm uses "username" field, but we treat it as email
    result = await db.execute(select(model.User).where(func.lower(model.User.email) == form_data.username.lower()))
    user = result.scalars().first()


    # Verify user exists and password is correct
    # Don't reveal which one failed (security best practice)
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW.Authenticate": "Bearer"}

        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")

@router.get("/me", response_model=UserPrivate)
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get the currently authenticated user."""
    user_id = verify_access_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate user_id is a valid integer (defense against malformed JWT)
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(
        select(model.User).where(model.User.id == user_id_int),
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


@router.get(
    "/{user.id}",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
)
async def get_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(model.User).where(model.User.id == user_id)
    )

    user = result.scalars().first()
    if user:
        return user
    raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="user not found",
    )

@router.get("/{user_id}/posts", response_model=list[PostResponse])
async def get_user_posts(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(model.User).where(model.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    result =await db.execute(
    select(model.Post)
    .options(selectinload(model.Post.author))
    .where(model.Post.user_id == user_id)
    )
    posts = result.scalars().all()
    return posts


@router.patch("/{user_id}", response_model=UserPrivate)
async def update_user(user_id: int, user_update:UserUpdate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(model.User).where(model.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    if user_update.username is not None and user_update.username.lower() != user.username.lower():
        result = await db.execute(select(model.User).where(func.lower(model.User.username) == user_update.username.lower()))
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="username already exist",
        )

    if user_update.email is not None and user_update.email.lower() != user.email.lower():
        result = await db.execute(select(model.User).where(func.lower(model.User.email) == user_update.email.lower()))
        existing_email = result.scalars().first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="email already exist",
        )

    if user_update.username is not None:
        user.username = user_update.username
    if user_update.email is not None:
        user.email.lower = user_update.email.lower()
    if user_update.image_path is not None:
        user.image_path = user_update.image_path
    
    await db.commit()
    await db.refresh(user)
    return user

    
@router.delete(
    "/{user.id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(model.User).where(model.User.id == user_id)
    )

    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="user not found",
        )
        
    await db.delete(user)
    await db.commit()

