from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import timedelta

from app.core.config import settings
from app.core import security
from app.crud import crud_users
from app.schemas import token
from app.api.v1.deps import get_database
from app.core.logging import create_activity_log

router = APIRouter()

@router.post("/login", response_model=token.Token)
async def login_for_access_token(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_database), 
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Login user dan mengembalikan Bearer Token dengan logging aktivitas.
    """
    user = await crud_users.get_user_by_login_id(db, login_id=form_data.username)
    
    # Handle failed login
    if not user or not security.verify_password(form_data.password, user["hashed_password"]):
        log_user_data = {
            "_id": "ANONYMOUS",
            "login_id": form_data.username,
            "roles": ["anonymous"]
        } if not user else user
        
        background_tasks.add_task(
            create_activity_log,
            db=db,
            request=request,
            user_data=log_user_data,
            activity="USER_LOGIN_FAILED",
            description=f"Failed login attempt for user '{form_data.username}'",
            status="FAILED",
            details={
                "method": request.method,
                "endpoint": str(request.url),
                "client": request.client.host if request.client else None
            }
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect Login ID or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Handle successful login
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": str(user["_id"])},  # Menggunakan _id sebagai subjek token
        expires_delta=access_token_expires
    )
    
    # Log successful login
    background_tasks.add_task(
        create_activity_log,
        db=db,
        request=request,
        user_data=user,
        activity="USER_LOGIN",
        description=f"User '{user['login_id']}' logged in successfully",
        status="SUCCESS",
        details={
            "method": request.method,
            "endpoint": str(request.url),
            "user_id": str(user["_id"])
        }
    )
    
    return {"access_token": access_token, "token_type": "bearer"}