from fastapi import FastAPI, Request, HTTPException, status, Depends, APIRouter
from typing import Annotated
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from schemas import PostCreate, PostResponse, PostUpdate
import model
from database import Base, engine, get_db
from auth import CurrentUser

router = APIRouter()

@router.get("", response_model=list[PostResponse])
async def get_posts(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(model.Post).options(selectinload(model.Post.author)).order_by(model.Post.date_posted.desc()))
    posts = result.scalars().all()
    return posts

@router.post(
    "",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_post(post: PostCreate, current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    # result =await db.execute(
    #     select(model.User).where(model.User.id == post.user_id)
    # )

    # existing_user = result.scalars().first()
    # if not existing_user:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="user not found",
    #     )

    new_post = model.Post(
        title=post.title,
        content=post.content,
        user_id=current_user.id,
    )
    db.add(new_post)
    await db.commit()
    await db.refresh(new_post, attribute_names=["author"])
    return new_post


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result =await db.execute(select(model.Post).options(selectinload(model.Post.author)).where(model.Post.id == post_id))
    post = result.scalars().first()
    if post:
        return post
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

@router.put("/{post_id}", response_model=PostResponse)
async def update_posts(post_id: int, post_data:PostCreate, current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    result =await  db.execute(select(model.Post).where(model.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    # if post_data.user_id != post.user_id:
    #     result = db.execute(select(model.Post).where(model.User.id == post_data.user_id))
    #     user = result.scalars().first()
    #     if not user:
    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="not authorized to update this post",
        )
    

    post.title = post_data.title
    post.content = post_data.content

    await db.commit()
    await db.refresh(post, attribute_names=["author"])
    return post

@router.patch("/{post_id}", response_model=PostResponse)
async def update_posts_partial(post_id: int, post_data:PostUpdate, current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(model.Post).where(model.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="not authorized to update this post",
        )

    update_data = post_data.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(post, key, val)
    
    await db.commit()
    await db.refresh(post, attribute_names=["author"])
    return post

@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: int, current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(model.Post).where(model.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="not authorized to delete this post",
        )
    
    await db.delete(post)
    await db.commit()