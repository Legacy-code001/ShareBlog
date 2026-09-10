from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.responses import HTMLResponse
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHttpException
from schemas import PostCreate, PostResponse, UserResponse, UserCreate, PostCreate, PostUpdate, UserUpdate
from sqlalchemy import select
from sqlalchemy.orm import session
from typing import Annotated
import model
from database import Base, engine, get_db

# Creates every table registered under this specific Base
Base.metadata.create_all(bind=engine) 

app = FastAPI()
templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")


# posts: list[dict] = [
#     {
#         "id": 1,
#         "author": "Abdulraheem Abdulmueez",
#         "title": "FastAPI is Awesome",
#         "content": "This framework is really easy to use and super fast.",
#         "date_posted": "April 20, 2026",
#     },
#     {
#         "id": 2,
#         "author": "Taiwo Raheem",
#         "title": "Python is Great for Web Development",
#         "content": "Python is a great language for web development, and FastAPI makes it even better.",
#         "date_posted": "April 21, 2026",
#     },
# ]



@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
def home(request: Request, db: Annotated[session, Depends(get_db)]):
    result = db.execute(select(model.Post))
    posts = result.scalars().all()
    return templates.TemplateResponse(
        request,
        "home.html",
        {"posts": posts, "title": "Home"},
    )

@app.get("/posts/{post_id}", include_in_schema=False)
def post_page(request: Request, post_id: int, db: Annotated[session, Depends(get_db)]):
    result = db.execute(
        select(model.Post).where(model.Post.id == post_id)
    )
    post = result.scalars().first()
    if post:
        title = post.title[:50]
        return templates.TemplateResponse(
            request,
            "post.html",
            {"post": post, "title": title},
        )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


@app.get("/users/{user_id}/posts", include_in_schema=False, name="user_posts")
def user_posts_page(request: Request, user_id: int, db: Annotated[session, Depends(get_db)]):
    result = db.execute(select(model.User).where(model.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    result = db.execute(select(model.Post).where(model.Post.user_id == user_id))
    posts = result.scalars().all()
    return templates.TemplateResponse(
        request,
        "user_posts.html",
        {"posts": posts, "user": user, "title": f"{user.username}'s Posts"},
    )




@app.post(
    "/api/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(user: UserCreate, db: Annotated[session, Depends(get_db)]):
    result = db.execute(
        select(model.User).where(model.User.username == user.username),
    )

    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user already exit",
        )
    
    
    result = db.execute(
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
        email=user.email
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.get(
    "/api/users/{user.id}",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def get_user(user_id: int, db: Annotated[session, Depends(get_db)]):
    result = db.execute(
        select(model.User).where(model.User.id == user_id)
    )

    user = result.scalars().first()
    if user:
        return user
    raise HTTPException(
            status_code=status.HTTP_404_BAD_NOT_FOUND,
            detail="user not found",
    )

@app.delete(
    "/api/users/{user.id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_user(user_id: int, db: Annotated[session, Depends(get_db)] ):
    result = db.execute(
        select(model.User).where(model.User.id == user_id)
    )

    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_BAD_NOT_FOUND,
            detail="user not found",
        )
        
    db.delete(user)
    db.commit()



@app.get("/api/users/{user_id}/posts", response_model=list[PostResponse])
def get_user_posts(user_id: int, db: Annotated[session, Depends(get_db)]):
    result = db.execute(select(model.User).where(model.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    result = db.execute(select(model.Post).where(model.Post.user_id == user_id))
    posts = result.scalars().all()
    return posts


@app.patch("/api/users/{user_id}", response_model=PostResponse)
def update_user(user_id: int, user_update:UserUpdate, db: Annotated[session, Depends(get_db)]):
    result = db.execute(select(model.User).where(model.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    if user_update.username is not None and user_update.username != user.user_id:
        result = db.execute(select(model.User).where(model.User.id == user_update.user_id))
        user = result.scalars().first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="username already exist",
        )

    if user_update.email is not None and user_update.email != user.email:
        result = db.execute(select(model.User).where(model.User.email == user_update.email))
        user = result.scalars().first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="email already exist",
        )

    if user_update.username is not None:
        user.username = user_update.username
    if user_update.email is not None:
        user.email = user_update.email
    if user_update.image_path is not None:
        user.image_path = user_update.image_path
    
    db.commit()
    db.refresh(user)
    return user


@app.delete(
    "/api/users/{user.id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_user(user_id: int, db: Annotated[session, Depends(get_db)]):
    result = db.execute(
        select(model.User).where(model.User.id == user_id)
    )

    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_BAD_NOT_FOUND,
            detail="user not found",
        )
        
    db.delete(user)
    db.commit()


@app.get("/api/posts", response_model=list[PostResponse])
def get_posts(db: Annotated[session, Depends(get_db)]):
    result = db.execute(select(model.Post))
    posts = result.scalars().all()
    return posts


@app.post(
    "/api/posts",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_post(post: PostCreate, db: Annotated[session, Depends(get_db)]):
    result = db.execute(
        select(model.User).where(model.User.id == post.user_id)
    )

    existing_user = result.scalars().first()
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user not found",
        )

    new_post = model.Post(
        title=post.title,
        content=post.content,
        user_id=post.user_id,
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post

@app.get("/api/posts/{post_id}", response_model=PostResponse)
def get_post(post_id: int, db: Annotated[session, Depends(get_db)]):
    result = db.execute(select(model.Post).where(model.Post.id == post_id))
    post = result.scalars().first()
    if post:
        return post
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

#on this
@app.put("/api/posts/{post_id}", response_model=PostResponse)
def update_posts(post_id: int, post_data:PostCreate, db: Annotated[session, Depends(get_db)]):
    result = db.execute(select(model.Post).where(model.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    if post_data.user_id != post.user_id:
        result = db.execute(select(model.Post).where(model.User.id == post_data.user_id))
        user = result.scalars().first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user not found",
        )
    

    post.title = post_data.title
    post.content = post_data.content
    post.user_id = post_data.user_id

    db.commit()
    db.refresh(post)
    return post


@app.patch("/api/posts/{post_id}", response_model=PostResponse)
def update_posts_partial(post_id: int, post_data:PostUpdate, db: Annotated[session, Depends(get_db)]):
    result = db.execute(select(model.Post).where(model.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    update_data = post_data.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(post, key, val)
    
    db.commit()
    db.refresh(post)
    return post

@app.delete("/api/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: int, db: Annotated[session, Depends(get_db)]):
    result = db.execute(select(model.Post).where(model.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    
    db.delete(post)
    db.commit()






## StarletteHTTPException Handler
@app.exception_handler(StarletteHttpException)
def general_http_exception_handler(request: Request, exception: StarletteHttpException):
    message = (
        exception.detail
        if exception.detail
        else "An erroe occur, please check your request and try again"
    )

    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code = exception.status_code,
            content = {"detail": message}
        )
    return templates.TemplateResponse(
                request,
                "error.html",
                {
                    "status_code": exception.status_code, 
                    "title": exception.status_code, 
                    "message": message 
                },
                status_code=exception.status_code
    )
    
## RequestValidationError Handler
@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exception:RequestValidationError):
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content = {"detail": exception.errors()}
        )
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid request. Please check your input and try again.",
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )