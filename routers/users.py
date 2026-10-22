from fastapi import FastAPI, Request, HTTPException, Query, status, Depends, APIRouter, UploadFile, BackgroundTasks
from botocore.exceptions import ClientError
from typing import Annotated
from sqlalchemy import delete as sql_delete
from sqlalchemy import select
from datetime import UTC, datetime, timedelta
from auth import create_access_token,hash_password, oauth2_scheme, verify_password, verify_access_token, CurrentUser, generate_reset_token, hash_token_reset
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import selectinload
from config import settings
from image_utils import process_profile_image, delete_profile_image, upload_profile_image
from sqlalchemy import func, select
from starlette.concurrency import run_in_threadpool
from PIL import UnidentifiedImageError
from email_utils import send_password_reset_email
from sqlalchemy.ext.asyncio import AsyncSession
from schemas import ChangePasswordRequest, ForgetPasswordRequest, PaginatedPostResponse, PostResponse, ResetPasswordRequest, Token, UserCreate, UserPrivate, UserPublic, UserUpdate 
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

#the same me checks is use in current_user
@router.get("/me", response_model=UserPrivate)
async def get_current_user(
    current_user: CurrentUser
):
    return current_user



@router.post("/forget-password", status_code=status.HTTP_202_ACCEPTED)
async def forget_password(request_data:ForgetPasswordRequest, background_task:BackgroundTasks, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(model.User).where(func.lower(model.User.email) == request_data.email.lower()))

    user = result.scalars().first()
    if user:
        await db.execute(sql_delete(model.PasswordResetToken).where(model.PasswordResetToken.user_id == user.id))

    
        token=generate_reset_token()
        token_hash=hash_token_reset(token)
        expires_at= datetime.now(UTC) + timedelta(
            minutes=settings.reset_token_expire_minutes
        )
        
        reset_token = model.PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expired_at=expires_at
        )

        db.add(reset_token)
        await db.commit()

        background_task.add_task(
            send_password_reset_email,
            to_mail=user.email,
            username=user.username,
            token=token,
        )

        return {
            "message": "If an account exists with this email, you will receive password reset instructions.",
        }

@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(request_data: ResetPasswordRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    token_hash = hash_token_reset(request_data.token)
    result = await db.execute(select(model.PasswordResetToken).where(model.PasswordResetToken.token_hash == token_hash))

    reset_token = result.scalars().first()

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="nvalid or expired reset "
        )

    #this method ( .replace(tzinfo=UTC) ) is used on expired at sqlachemy did not captures the time zone info
    if reset_token.expired_at < datetime.now(UTC):
        await db.delete(reset_token)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="nvalid or expired reset"
        )

    result = await db.execute(select(model.User).where(model.User.id== reset_token.user_id))

    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="invalid or expires token"
        )
    
    user.password_hash = hash_password(request_data.new_password)

    await db.execute(sql_delete(model.PasswordResetToken).where(model.PasswordResetToken.user_id == user.id))

    await db.commit()

    return {
        "message": "Password reset successfully. You can now log in with your new password.",
    }

@router.patch("/me/password", status_code=status.HTTP_200_OK)
async def changePassword(password_data: ChangePasswordRequest, current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):

    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )

    current_user.password_hash = hash_password(password_data.new_password)

    await db.execute(sql_delete(model.PasswordResetToken).where(model.PasswordResetToken.user_id == current_user.id))
    await db.commit()

   


    return {"message": "Password changed successfully"}

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

@router.get("/{user_id}/posts", response_model=PaginatedPostResponse)
async def get_user_posts(user_id: int, db: Annotated[AsyncSession, Depends(get_db)], skip: Annotated[int, Query(ge=0)] = 0, limit: Annotated[int, Query(ge=1, le=100)] = settings.post_per_page):
    result = await db.execute(select(model.User).where(model.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    count_result = await db.execute(select(func.count()).select_from(model.Post).where(model.Post.user_id == user_id))

    total = count_result.scalar() or 0
    result = await db.execute(
        select(model.Post)
        .options(selectinload(model.Post.author))
        .where(model.Post.user_id == user_id)
        .order_by(model.Post.date_posted.desc())
        .offset(skip)
        .limit(limit),
    )
    posts = result.scalars().all()
    has_more = skip + len(posts) < total
    return PaginatedPostResponse (
        posts=[PostResponse.model_validate(post) for post in posts],
        total=total,
        skip=skip,
        limit=limit,
        has_more=has_more,
    )


@router.patch("/{user_id}", response_model=UserPrivate)
async def update_user(user_id: int, user_update:UserUpdate, current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user",
        )
        
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
        user.email = user_update.email.lower()
    # if user_update.image_path is not None:
    #     user.image_path = user_update.image_path
    
    await db.commit()
    await db.refresh(user)
    return user

    
@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_user(user_id: int, current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="not authorized to update this post",
        )
    result = await db.execute(
        select(model.User).where(model.User.id == user_id)
    )

    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="user not found",
        )

    old_filename = user.image_file
        
    await db.delete(user)
    await db.commit()

    if old_filename:
        await delete_profile_image(old_filename)

@router.patch("/{user_id}/picture", response_model=UserPrivate)
async def upload_profile_picture(user_id: int, current_user: CurrentUser, file: UploadFile, db: Annotated[AsyncSession, Depends(get_db)]):
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user's picture"
        )

    content = await file.read()

    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {settings.max_upload_size_bytes // (1024 * 1024)}MB"
        )

    try:
        processed_bytes, new_file = await run_in_threadpool(process_profile_image, content)
    except UnidentifiedImageError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file. Please upload a valid image (JPEG, PNG, GIF, WebP).",
        ) from err

    # Upload to S3 (also runs in threadpool via async wrapp
    try:
        await upload_profile_image(processed_bytes, new_file)
    except ClientError as err:
        raise Exception(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload image. Please try again."
        ) from err


    
    old_filename = current_user.image_file

    current_user.image_file = new_file

    await db.commit()
    await db.refresh(current_user)

    if old_filename:
        await delete_profile_image(old_filename)

    return current_user

@router.delete("/{user_id}/picture", response_model=UserPrivate)
async def delete_profile_picture(user_id: int, current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this user's picture"
        )
    
    
    old_filename = current_user.image_file
    print(type(current_user.image_file), repr(current_user.image_file))

    if not old_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No profile picture to delete"
        )
        
    current_user.image_file = None
    await db.commit()
    await db.refresh(current_user)

    await delete_profile_image(old_filename)

    return current_user
        