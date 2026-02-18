import random
import string
import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, status, Depends, UploadFile, File, Response, Query, Form, Header
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.requests import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.gzip import GZipMiddleware
from datetime import datetime
from typing import List, Optional
from bson import ObjectId
import bcrypt
from pydantic import ValidationError
import os

from database.schema import (
    UserRegister, UserLogin, UserResponse, UserUpdate,
    TaskCreate, TaskUpdate, TaskResponse, Token, Message,
    OTPRequest, OTPVerification, PreRegistrationUser, RegistrationWithOTP, OTPResponse,
    ProfilePictureResponse, PasswordChange, UserSettings,
    ForgotPasswordRequest, ResetPasswordRequest,
    CommentCreate, CommentUpdate, CommentResponse,
    TaskHistoryResponse, SettingsHistoryResponse, SettingsRollbackRequest,
    TaskAttachmentResponse, TaskTemplateCreate, TaskTemplateResponse,
    CategoryCreate, CategoryResponse
)
from database.models import TaskStatus
from config import (
    users_collection, tasks_collection, 
    password_reset_tokens_collection, 
    task_history_collection, 
    comments_collection,
    settings_history_collection,
    task_attachments_collection,
    task_templates_collection,
    categories_collection
)
from email_service import send_registration_otp, verify_registration_otp
from image_utils import upload_profile_picture, delete_profile_picture, validate_image
from auth_utils import create_access_token, create_refresh_token, verify_token, get_user_id_from_token

app = FastAPI(title="Task Management System", version="1.0.0")

# Utility function to run synchronous MongoDB operations in async context
async def run_db_operation(func, *args, **kwargs):
    """Run synchronous MongoDB operations in async context"""
    return await asyncio.to_thread(func, *args, **kwargs)

# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check"""
    return {"status": "healthy", "service": "Task Management System"}

@app.get("/health/db")
async def database_health_check():
    """Database health check"""
    try:
        # Try to ping the database
        await asyncio.to_thread(users_collection.find_one, {"_id": ObjectId("000000000000000000000000")})
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

@app.get("/health/ready")
async def readiness_check():
    """Readiness probe for deployment"""
    try:
        # Check database connection
        await asyncio.to_thread(users_collection.count_documents, {})
        return {"status": "ready", "checks": {"database": "ok"}}
    except Exception as e:
        return {"status": "not ready", "checks": {"database": "failed"}, "error": str(e)}

# Authentication dependency
async def get_current_user(token: str = Header(..., description="Bearer token")):
    """Dependency to get current authenticated user"""
    if not token.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme"
        )
    
    token = token[7:]  # Remove "Bearer " prefix
    payload = verify_token(token, "access")
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user = await asyncio.to_thread(users_collection.find_one, {"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user

# Custom validation error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Custom handler for validation errors"""
    error_details = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"][1:])  # Skip 'body'
        message = error["msg"]
        error_details.append(f"{field}: {message}")
    
    # Debug: Print validation errors
    print(f"Validation error: {error_details}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation failed",
            "errors": error_details,
            "message": "Please check your input and try again."
        }
    )

# CORS middleware - Configure from environment
import os
from dotenv import load_dotenv
load_dotenv()

# Get allowed origins from environment or use defaults
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add GZip middleware for compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Middleware to add cache control headers
@app.middleware("http")
async def add_cache_control_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static"):
        # Cache static assets for 1 year
        response.headers["Cache-Control"] = "public, max-age=31536000"
    elif request.url.path in ["/login", "/register", "/"]:
        # Prevent caching of auth pages
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    else:
        # Default cache control for other pages
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
    return response

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# Helper functions
def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hashed password"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def user_helper(user) -> dict:
    """Helper function to convert MongoDB user document to dict"""
    return {
        "id": str(user["_id"]),
        "username": user["username"],
        "first_name": user["first_name"],
        "last_name": user["last_name"],
        "email": user["email"],
        "phone_number": user["phone_number"],
        "created_at": user["created_at"],
        "profile_image": user.get("profile_image"),
        "profile_thumbnail": user.get("profile_thumbnail"),
        "bio": user.get("bio"),
        "settings": user.get("settings"),
        "email_verified": user.get("email_verified"),
        "is_active": user.get("is_active")
    }


def task_helper(task) -> dict:
    """Helper function to convert MongoDB task document to dict"""
    # Count subtasks
    subtask_count = 0
    if task.get("_id"):
        subtask_count = tasks_collection.count_documents({"parent_task_id": str(task["_id"])})
    
    return {
        "id": str(task["_id"]),
        "title": task["title"],
        "description": task["description"],
        "status": task["status"],
        "priority": task["priority"],
        "user_id": task["user_id"],
        "due_date": task.get("due_date"),
        "start_time": task.get("start_time"),
        "end_time": task.get("end_time"),
        "created_at": task["created_at"],
        "updated_at": task["updated_at"],
        "tags": task.get("tags", []),
        "assigned_to": task.get("assigned_to"),
        "notes": task.get("notes"),
        "parent_task_id": task.get("parent_task_id"),
        "subtask_count": subtask_count,
        "is_subtask": task.get("parent_task_id") is not None
    }


# Logout Route
@app.get("/logout")
async def logout(response: Response):
    """Logout user and clear session"""
    response = RedirectResponse(url="/login")
    response.set_cookie("token", "", max_age=0, httponly=True, secure=True, samesite="lax")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# HTML Routes
@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Landing page"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Register page"""
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Task dashboard page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/task/{task_id}", response_class=HTMLResponse)
async def task_detail_page(request: Request, task_id: str):
    """Task detail page"""
    return templates.TemplateResponse("task_detail.html", {"request": request, "task_id": task_id})


@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    """User profile page"""
    return templates.TemplateResponse("profile.html", {"request": request})


@app.get("/test-profile-picture", response_class=HTMLResponse)
async def test_profile_picture_page(request: Request):
    """Profile picture upload test page"""
    return templates.TemplateResponse("profile_picture_test.html", {"request": request})


# API Routes - Authentication & OTP

@app.get("/api/auth/check-email", response_model=dict)
async def check_email_exists(email: str = Query(..., description="Email to check")):
    """Check if an email already exists in the system"""
    # Check if MongoDB is connected
    if users_collection is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed. Please check server logs."
        )
    
    # Basic email format validation
    if "@" not in email or "." not in email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )
    
    # Check if email exists in the database  
    existing_user = await asyncio.to_thread(users_collection.find_one, {"email": email.lower().strip()})
    
    return {"exists": existing_user is not None}


@app.get("/api/auth/check-phone", response_model=dict)
async def check_phone_exists(phone: str = Query(..., description="Phone number to check")):
    """Check if a phone number already exists in the system"""
    import re
    
    # Remove all non-digit characters
    cleaned_phone = re.sub(r'\D', '', phone)
    
    # Validate 10-digit Indian mobile number
    if not re.match(r'^[6-9]\d{9}$', cleaned_phone):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please enter a valid 10-digit Indian mobile number starting with 6-9"
        )
    
    # Check if phone exists in the database (exact match on cleaned number)
    existing_user = await asyncio.to_thread(
        users_collection.find_one, 
        {
            "$or": [
                {"phone_number": cleaned_phone},
                {"phone_number": {"$regex": f"^\\+?{re.escape(cleaned_phone)}$", "$options": "i"}}
            ]
        }
    )
    
    return {"exists": existing_user is not None}
@app.post("/api/auth/send-otp")
async def send_otp(request: Request):
    """Send OTP to email for registration verification"""
    try:
        # Debug: Print request details
        print(f"Request method: {request.method}")
        content_type = request.headers.get('content-type', '')
        print(f"Content-Type: {content_type}")
        
        # Parse request body - handle both JSON and form-urlencoded
        email = None
        if 'application/json' in content_type:
            try:
                body = await request.json()
                email = body.get('email')
            except Exception as json_error:
                print(f"JSON parse error: {json_error}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid JSON in request body"
                )
        elif 'application/x-www-form-urlencoded' in content_type or 'form-urlencoded' in content_type:
            try:
                form_data = await request.form()
                email = form_data.get('email')
            except Exception as form_error:
                print(f"Form parse error: {form_error}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid form data"
                )
        else:
            # Try to parse as JSON as fallback
            try:
                body = await request.json()
                email = body.get('email')
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unsupported content type"
                )
        
        # Debug: Print received data
        print(f"Received OTP request - email: {email}")
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is required"
            )
        
        # Validate email format
        if not isinstance(email, str) or '@' not in email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )
        
        # Check if email already exists
        existing_user = await asyncio.to_thread(
            users_collection.find_one, 
            {"email": email}
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email address already exists"
            )
        
        # Send OTP
        result = await send_registration_otp(email)
        
        if result["success"]:
            return {"success": True, "message": "OTP sent successfully to your email"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["message"]
            )
            
    except HTTPException:
        raise
    except ValueError as e:
        print(f"Value error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request format"
        )
    except Exception as e:
        print(f"Send OTP error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send OTP: {str(e)}"
        )


@app.post("/api/auth/verify-otp", response_model=OTPResponse)
async def verify_otp(request: Request):
    """Verify OTP for email validation"""
    try:
        # Debug: Print request details
        content_type = request.headers.get('content-type', '')
        print(f"Verify OTP - Content-Type: {content_type}")
        
        # Parse request body - handle both JSON and form-urlencoded
        email = None
        otp = None
        
        if 'application/json' in content_type:
            try:
                body = await request.json()
                email = body.get('email')
                otp = body.get('otp')
            except Exception as json_error:
                print(f"JSON parse error: {json_error}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid JSON in request body"
                )
        elif 'application/x-www-form-urlencoded' in content_type or 'form-urlencoded' in content_type:
            try:
                form_data = await request.form()
                email = form_data.get('email')
                otp = form_data.get('otp')
            except Exception as form_error:
                print(f"Form parse error: {form_error}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid form data"
                )
        else:
            # Try to parse as JSON as fallback
            try:
                body = await request.json()
                email = body.get('email')
                otp = body.get('otp')
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unsupported content type"
                )
        
        print(f"Verify OTP - email: {email}, otp: {otp}")
        
        if not email or not otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both email and OTP are required"
            )
        
        # Verify OTP but don't consume it yet (it will be consumed during registration)
        result = verify_registration_otp(email, otp, consume=False)
        print(f"OTP verification result: {result}")
        
        if result["valid"]:
            return OTPResponse(success=True, message=result["message"])
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Verify OTP error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify OTP. Please try again."
        )


@app.post("/api/auth/register-with-otp", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register_user_with_otp(registration_data: RegistrationWithOTP):
    """Register a new user after OTP verification"""
    try:
        # Extract user data and OTP from request
        user = registration_data.user_data
        otp = registration_data.otp
        
        # Verify OTP and consume it during registration
        otp_result = verify_registration_otp(user.email, otp, consume=True)
        if not otp_result["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=otp_result["message"]
            )
        
        # Check if user already exists by email
        existing_email = await asyncio.to_thread(users_collection.find_one, {"email": user.email})
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email address already exists"
            )
        
        # Check if username already exists
        existing_username = await asyncio.to_thread(users_collection.find_one, {"username": user.username})
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This username is already taken"
            )
        
        # Create new user
        user_dict = user.dict()
        user_dict["password"] = hash_password(user.password)
        user_dict["created_at"] = datetime.utcnow()
        user_dict["updated_at"] = datetime.utcnow()
        user_dict["email_verified"] = True
        user_dict["is_active"] = True
        user_dict["profile_thumbnail"] = None
        
        # Insert user into database
        result = await asyncio.to_thread(users_collection.insert_one, user_dict)
        new_user = await asyncio.to_thread(users_collection.find_one, {"_id": result.inserted_id})
        
        if not new_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user account"
            )
        
        # Create JWT tokens
        access_token = create_access_token(data={"sub": str(new_user["_id"])})
        refresh_token = create_refresh_token(data={"sub": str(new_user["_id"])})
        
        # Return user with JWT tokens
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": user_helper(new_user)
        }
        
    except HTTPException:
        raise
    except ValidationError as e:
        error_messages = []
        for error in e.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            error_messages.append(f"{field}: {message}")
        
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Validation failed", "errors": error_messages}
        )
    except Exception as e:
        print(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during registration. Please try again."
        )


# Legacy registration endpoint (without OTP) - kept for backward compatibility
@app.post("/api/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserRegister):
    """Register a new user (legacy endpoint - use /register-with-otp for OTP verification)"""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Please use the OTP verification flow. First call /api/auth/send-otp, then /api/auth/register-with-otp"
    )


@app.post("/api/auth/login", response_model=Token)
async def login_user(user: UserLogin):
    """Login a user"""
    # Find user by email
    db_user = await asyncio.to_thread(users_collection.find_one, {"email": user.email})
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not verify_password(user.password, db_user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Create JWT tokens
    access_token = create_access_token(data={"sub": str(db_user["_id"])})
    refresh_token = create_refresh_token(data={"sub": str(db_user["_id"])})
    
    # Update last login
    await asyncio.to_thread(users_collection.update_one, 
        {"_id": db_user["_id"]},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    # Return user with JWT tokens
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user_helper(db_user)
    }


@app.post("/api/auth/refresh")
async def refresh_access_token(refresh_token_data: dict):
    """Refresh access token using refresh token"""
    try:
        refresh_token = refresh_token_data.get("refresh_token")
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token is required"
            )
        
        # Verify refresh token
        payload = verify_token(refresh_token, "refresh")
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Check if user exists and is active
        user = await asyncio.to_thread(users_collection.find_one, {"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive"
            )
        
        # Create new access token
        new_access_token = create_access_token(data={"sub": str(user["_id"])})
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh token"
        )


# API Routes - Users
@app.get("/api/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """Get user by ID"""
    try:
        user = await asyncio.to_thread(users_collection.find_one, {"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user_helper(user)
    except:
        raise HTTPException(status_code=400, detail="Invalid user ID")


@app.put("/api/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, user_update: UserUpdate):
    """Update user profile"""
    try:
        update_data = {k: v for k, v in user_update.dict().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="No data to update")
        
        update_data["updated_at"] = datetime.utcnow()
        
        result = await asyncio.to_thread(users_collection.update_one, 
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        updated_user = await asyncio.to_thread(users_collection.find_one, {"_id": ObjectId(user_id)})
        return user_helper(updated_user)
    except HTTPException:
        raise
    except:
        raise HTTPException(status_code=400, detail="Invalid user ID")


@app.post("/api/users/{user_id}/upload-profile-picture", response_model=ProfilePictureResponse)
async def upload_user_profile_picture(user_id: str, file: UploadFile = File(...)):
    """Upload profile picture for a user"""
    try:
        # Validate user exists
        user = await asyncio.to_thread(users_collection.find_one, {"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Process and save the image
        result = await upload_profile_picture(file, user_id)
        
        if result["success"]:
            # Delete old profile picture if exists
            old_profile_image = user.get("profile_image")
            if old_profile_image:
                # Extract filename from path
                old_filename = os.path.basename(old_profile_image)
                delete_profile_picture(old_filename)
            
            # Update user's profile_image field in database
            await asyncio.to_thread(users_collection.update_one, 
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "profile_image": result["file_path"],
                        "profile_thumbnail": result["thumbnail_path"],
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            return ProfilePictureResponse(
                success=True,
                message="Profile picture uploaded successfully",
                file_path=result["file_path"],
                thumbnail_path=result["thumbnail_path"],
                original_filename=result["original_filename"]
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to process image")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Profile picture upload error: {e}")
        raise HTTPException(status_code=400, detail="Invalid user ID or upload failed")




@app.get("/api/users/{user_id}/profile-picture")
async def get_user_profile_picture(user_id: str):
    """Get user's profile picture information"""
    try:
        user = await asyncio.to_thread(users_collection.find_one, {"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        profile_image = user.get("profile_image")
        profile_thumbnail = user.get("profile_thumbnail")
        
        if not profile_image:
            return {
                "has_profile_picture": False,
                "message": "No profile picture found"
            }
        
        return {
            "has_profile_picture": True,
            "profile_image": profile_image,
            "profile_thumbnail": profile_thumbnail,
            "message": "Profile picture found"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get profile picture error: {e}")
        raise HTTPException(status_code=400, detail="Invalid user ID")


@app.post("/api/users/{user_id}/change-password", response_model=Message)
async def change_user_password(user_id: str, password_data: PasswordChange):
    """Change user password"""
    try:
        # Validate user exists
        user = await asyncio.to_thread(users_collection.find_one, {"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Verify current password
        if not verify_password(password_data.current_password, user["password"]):
            raise HTTPException(
                status_code=400, 
                detail="Current password is incorrect"
            )
        
        # Check if new password is different from current
        if verify_password(password_data.new_password, user["password"]):
            raise HTTPException(
                status_code=400,
                detail="New password must be different from current password"
            )
        
        # Hash new password
        new_password_hash = hash_password(password_data.new_password)
        
        # Update password in database
        result = await asyncio.to_thread(users_collection.update_one, 
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "password": new_password_hash,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Password change error: {e}")
        raise HTTPException(status_code=400, detail="Invalid user ID or password change failed")


@app.put("/api/users/{user_id}/settings")
async def update_user_settings(user_id: str, settings: UserSettings, request: Request):
    """Update user settings"""
    try:
        # Get current user for history tracking
        current_user = await get_current_user_from_token(request)
        changed_by = str(current_user["_id"]) if current_user else "system"
        
        # Validate user exists
        user = await asyncio.to_thread(users_collection.find_one, {"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get old settings
        old_settings = user.get("settings", {})
        
        # Update settings
        settings_dict = settings.dict()
        await asyncio.to_thread(users_collection.update_one, 
            {"_id": ObjectId(user_id)},
            {"$set": {"settings": settings_dict, "updated_at": datetime.utcnow()}}
        )
        
        # Track settings history
        history_entry = {
            "user_id": user_id,
            "settings": old_settings,
            "changed_by": changed_by,
            "created_at": datetime.utcnow(),
            "change_reason": "Settings updated"
        }
        await asyncio.to_thread(settings_history_collection.insert_one, history_entry)
        
        return {"message": "Settings updated successfully", "settings": settings_dict}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Settings update error: {e}")
        raise HTTPException(status_code=400, detail="Invalid user ID or settings update failed")


@app.get("/api/users/{user_id}/settings")
async def get_user_settings(user_id: str):
    """Get user settings"""
    try:
        user = await asyncio.to_thread(users_collection.find_one, {"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        settings = user.get("settings", {})
        
        # Return default settings if none exist
        if not settings:
            default_settings = UserSettings().dict()
            return {"settings": default_settings}
        
        return {"settings": settings}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get settings error: {e}")
        raise HTTPException(status_code=400, detail="Invalid user ID")


# API Routes - Tasks
@app.post("/api/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(task: TaskCreate, user_id: str):
    """Create a new task"""
    task_dict = task.dict()
    task_dict["user_id"] = user_id
    task_dict["created_at"] = datetime.utcnow()
    task_dict["updated_at"] = datetime.utcnow()
    
    result = await asyncio.to_thread(tasks_collection.insert_one, task_dict)
    new_task = await asyncio.to_thread(tasks_collection.find_one, {"_id": result.inserted_id})
    
    return task_helper(new_task)


@app.get("/api/tasks", response_model=List[TaskResponse])
async def get_tasks(user_id: str, status: Optional[TaskStatus] = None):
    """Get all tasks for a user, optionally filtered by status"""
    query = {"user_id": user_id}
    if status:
        query["status"] = status
    
    tasks = await asyncio.to_thread(
        lambda: list(tasks_collection.find(query).sort("created_at", -1))
    )
    return [task_helper(task) for task in tasks]


@app.get("/api/tasks/{user_id}/search")
async def search_tasks(
    user_id: str,
    q: Optional[str] = Query(None, description="Search query"),
    status: Optional[TaskStatus] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    sort_by: Optional[str] = Query("created_at", description="Sort by field"),
    sort_order: Optional[str] = Query("desc", description="Sort order: asc or desc")
):
    """Search and filter tasks"""
    try:
        query = {"user_id": user_id}
        
        # Add status filter
        if status:
            query["status"] = status
        
        # Add priority filter
        if priority:
            query["priority"] = priority
        
        # Add text search
        if q:
            query["$or"] = [
                {"title": {"$regex": q, "$options": "i"}},
                {"description": {"$regex": q, "$options": "i"}},
                {"tags": {"$regex": q, "$options": "i"}}
            ]
        
        # Determine sort order
        sort_direction = -1 if sort_order == "desc" else 1
        
        # Get tasks
        tasks = await asyncio.to_thread(
            lambda: list(tasks_collection.find(query).sort(sort_by, sort_direction))
        )
        
        return [task_helper(task) for task in tasks]
        
    except Exception as e:
        print(f"Search error: {e}")
        raise HTTPException(status_code=500, detail="Failed to search tasks")


@app.get("/api/tasks/{task_id}/activity")
async def get_task_activity(task_id: str):
    """Get task activity history"""
    return []


@app.get("/api/tasks/{task_id}/history")
async def get_task_history(task_id: str):
    """Get task change history"""
    # For now, return empty array to fix the JavaScript error
    # TODO: Fix MongoDB collection issue
    return []


@app.get("/api/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """Get a specific task by ID"""
    try:
        task = await asyncio.to_thread(tasks_collection.find_one, {"_id": ObjectId(task_id)})
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task_helper(task)
    except HTTPException:
        raise
    except:
        raise HTTPException(status_code=400, detail="Invalid task ID")


@app.put("/api/tasks/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, task_update: TaskUpdate, request: Request):
    """Update a task"""
    try:
        # Get current user for history tracking
        user = await get_current_user_from_token(request)
        changed_by = str(user["_id"]) if user else "system"
        
        # Get current task to check existing values
        current_task = await asyncio.to_thread(tasks_collection.find_one, {"_id": ObjectId(task_id)})
        if not current_task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        user_id = current_task["user_id"]
        
        update_data = {k: v for k, v in task_update.dict().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="No data to update")
        
        # Handle special fields from drag-and-drop
        if "start_time_if_empty" in update_data:
            # Only set start_time if it's not already set
            if not current_task.get("start_time"):
                update_data["start_time"] = update_data["start_time_if_empty"]
            del update_data["start_time_if_empty"]
        
        # Auto-set start time when moving to in_progress (if not already set)
        if update_data.get("status") == "in_progress" and not current_task.get("start_time"):
            update_data["start_time"] = datetime.utcnow()
        
        # Auto-set end time when completing task (if not already set)
        if update_data.get("status") == "completed" and not current_task.get("end_time"):
            update_data["end_time"] = datetime.utcnow()
        
        # Clear end time when reopening completed task
        if current_task.get("status") == "completed" and update_data.get("status") != "completed":
            update_data["end_time"] = None
        
        update_data["updated_at"] = datetime.utcnow()
        
        # Track history for each changed field
        for field_name, new_value in update_data.items():
            if field_name == "updated_at":
                continue
            
            old_value = current_task.get(field_name)
            
            # Only create history if value actually changed
            if old_value != new_value:
                await create_task_history_entry(
                    task_id=task_id,
                    user_id=user_id,
                    changed_by=changed_by,
                    field_name=field_name,
                    old_value=old_value,
                    new_value=new_value
                )
        
        result = await asyncio.to_thread(tasks_collection.update_one, 
            {"_id": ObjectId(task_id)},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Task not found")
        
        updated_task = await asyncio.to_thread(tasks_collection.find_one, {"_id": ObjectId(task_id)})
        return task_helper(updated_task)
    except HTTPException:
        raise
    except:
        raise HTTPException(status_code=400, detail="Invalid task ID")


@app.delete("/api/tasks/{task_id}", response_model=Message)
async def delete_task(task_id: str):
    """Delete a task"""
    try:
        result = await asyncio.to_thread(tasks_collection.delete_one, {"_id": ObjectId(task_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"message": "Task deleted successfully"}
    except HTTPException:
        raise
    except:
        raise HTTPException(status_code=400, detail="Invalid task ID")


@app.get("/api/tasks/{user_id}/statistics")
async def get_task_statistics(user_id: str):
    """Get task statistics for a user"""
    try:
        # Get all tasks for the user
        pipeline = [
            {"$match": {"user_id": user_id}},
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }
            }
        ]
        
        status_counts = await asyncio.to_thread(
            lambda: list(tasks_collection.aggregate(pipeline))
        )
        
        # Initialize statistics
        statistics = {
            "total": 0,
            "todo": 0,
            "in_progress": 0,
            "completed": 0,
            "overdue": 0,
            "completed_today": 0,
            "completion_rate": 0
        }
        
        # Process status counts
        for item in status_counts:
            status = item["_id"]
            count = item["count"]
            statistics["total"] += count
            if status in statistics:
                statistics[status] = count
        
        # Get overdue and completed today tasks
        now = datetime.utcnow()
        today_start = datetime(now.year, now.month, now.day)
        
        overdue_count = await asyncio.to_thread(tasks_collection.count_documents, {
            "user_id": user_id,
            "status": {"$ne": "completed"},
            "due_date": {"$lt": now}
        })
        
        completed_today_count = await asyncio.to_thread(tasks_collection.count_documents, {
            "user_id": user_id,
            "status": "completed",
            "end_time": {"$gte": today_start}
        })
        
        statistics["overdue"] = overdue_count
        statistics["completed_today"] = completed_today_count
        
        # Calculate completion rate
        if statistics["total"] > 0:
            statistics["completion_rate"] = round(
                (statistics["completed"] / statistics["total"]) * 100, 2
            )
        
        return statistics
        
    except Exception as e:
        print(f"Statistics error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get task statistics")


# Helper function to get current user from JWT token (from cookie)
async def get_current_user_from_token(request: Request):
    """Helper to get current user from JWT token in cookie or Authorization header"""
    try:
        # Try to get token from cookie first
        token = request.cookies.get("token")
        
        # If no cookie, try to get from Authorization header
        if not token:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header[7:]  # Remove "Bearer " prefix
        
        if not token:
            return None
        
        payload = verify_token(token, "access")
        if payload is None:
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        user = await asyncio.to_thread(users_collection.find_one, {"_id": ObjectId(user_id)})
        return user
    except Exception as e:
        print(f"Error getting current user: {e}")
        return None


# ============================================================================
# NEW ENDPOINTS - Phase 1: Missing Core Features
# ============================================================================

@app.post("/api/auth/forgot-password")
async def forgot_password(request_data: ForgotPasswordRequest):
    """Request password reset - sends reset link via email"""
    try:
        # Check if user exists
        user = await asyncio.to_thread(users_collection.find_one, {"email": request_data.email})
        if not user:
            # Don't reveal if email exists for security
            return {"message": "If this email exists, a password reset link has been sent"}
        
        # Generate reset token
        import secrets
        reset_token = secrets.token_urlsafe(32)
        
        # Set expiry (1 hour from now)
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        # Store reset token
        reset_token_dict = {
            "email": request_data.email,
            "token": reset_token,
            "created_at": datetime.utcnow(),
            "expires_at": expires_at,
            "used": False
        }
        
        await asyncio.to_thread(password_reset_tokens_collection.insert_one, reset_token_dict)
        
        # TODO: Send email with reset link
        # This would integrate with your email service
        print(f"Password reset token for {request_data.email}: {reset_token}")
        
        return {"message": "If this email exists, a password reset link has been sent"}
        
    except Exception as e:
        print(f"Forgot password error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process password reset request")


@app.post("/api/auth/reset-password")
async def reset_password(request_data: ResetPasswordRequest):
    """Reset password using token"""
    try:
        # Find the token
        reset_token_doc = await asyncio.to_thread(
            password_reset_tokens_collection.find_one,
            {"token": request_data.token, "used": False}
        )
        
        if not reset_token_doc:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")
        
        # Check if token is expired
        if datetime.utcnow() > reset_token_doc["expires_at"]:
            raise HTTPException(status_code=400, detail="Reset token has expired")
        
        email = reset_token_doc["email"]
        
        # Update user's password
        new_password_hash = bcrypt.hashpw(
            request_data.new_password.encode('utf-8'), 
            bcrypt.gensalt()
        ).decode('utf-8')
        
        result = await asyncio.to_thread(
            users_collection.update_one,
            {"email": email},
            {"$set": {"password": new_password_hash, "updated_at": datetime.utcnow()}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Mark token as used
        await asyncio.to_thread(
            password_reset_tokens_collection.update_one,
            {"token": request_data.token},
            {"$set": {"used": True}}
        )
        
        return {"message": "Password has been reset successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Reset password error: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset password")


@app.post("/api/auth/resend-otp")
async def resend_otp(request_data: OTPRequest):
    """Resend OTP to email"""
    try:
        # Send OTP
        result = await send_registration_otp(request_data.email)
        
        if result["success"]:
            return {"success": True, "message": "OTP resent successfully to your email"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["message"]
            )
            
    except Exception as e:
        print(f"Resend OTP error: {e}")
        raise HTTPException(status_code=500, detail="Failed to resend OTP")


@app.get("/api/users/me", response_model=UserResponse)
async def get_current_user_profile(request: Request):
    """Get current user profile from JWT token"""
    user = await get_current_user_from_token(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return user_helper(user)


@app.delete("/api/users/me", response_model=Message)
async def delete_current_user(request: Request):
    """Delete current user account"""
    user = await get_current_user_from_token(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_id = str(user["_id"])
    
    try:
        # Delete user's tasks
        await asyncio.to_thread(
            tasks_collection.delete_many, 
            {"user_id": user_id}
        )
        
        # Delete user account
        result = await asyncio.to_thread(
            users_collection.delete_one, 
            {"_id": user["_id"]}
        )
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"message": "User account deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Delete user error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete user account")


@app.post("/api/tasks/{task_id}/ai-analyze")
async def analyze_task_ai(task_id: str):
    """Get AI suggestions for task (placeholder)"""
    try:
        task = await asyncio.to_thread(tasks_collection.find_one, {"_id": ObjectId(task_id)})
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Placeholder AI analysis
        suggestions = {
            "task_id": task_id,
            "suggestions": [
                "Consider breaking this into smaller subtasks",
                "This task might benefit from collaboration",
                "Estimated time: 2-4 hours based on similar tasks"
            ],
            "tags_suggestions": task.get("tags", []),
            "priority_recommendation": task.get("priority", "medium"),
            "note": "AI features are coming soon. This is a placeholder."
        }
        
        return suggestions
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"AI analyze error: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze task")


# ============================================================================
# Phase 2: Task History & Audit Trail
# ============================================================================

async def create_task_history_entry(task_id: str, user_id: str, changed_by: str, field_name: str, old_value, new_value, comment: Optional[str] = None):
    """Helper function to create task history entry"""
    try:
        history_entry = {
            "task_id": task_id,
            "user_id": user_id,
            "field_name": field_name,
            "old_value": str(old_value) if old_value is not None else None,
            "new_value": str(new_value) if new_value is not None else None,
            "changed_by": changed_by,
            "created_at": datetime.utcnow(),
            "comment": comment
        }
        
        await asyncio.to_thread(task_history_collection.insert_one, history_entry)
    except Exception as e:
        print(f"Error creating task history: {e}")


# ============================================================================
# Phase 3: Comment System
# ============================================================================

@app.post("/api/tasks/{task_id}/comments", response_model=CommentResponse)
async def create_comment(task_id: str, comment_data: CommentCreate, request: Request):
    """Add a comment to a task"""
    try:
        # Get current user
        user = await get_current_user_from_token(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Verify task exists
        task = await asyncio.to_thread(tasks_collection.find_one, {"_id": ObjectId(task_id)})
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Create comment
        comment_dict = {
            "task_id": task_id,
            "user_id": str(user["_id"]),
            "content": comment_data.content,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "edited": False,
            "parent_comment_id": comment_data.parent_comment_id
        }
        
        result = await asyncio.to_thread(comments_collection.insert_one, comment_dict)
        comment_doc = await asyncio.to_thread(comments_collection.find_one, {"_id": result.inserted_id})
        
        return {
            "id": str(comment_doc["_id"]),
            "task_id": comment_doc["task_id"],
            "user_id": comment_doc["user_id"],
            "content": comment_doc["content"],
            "created_at": comment_doc["created_at"],
            "updated_at": comment_doc["updated_at"],
            "edited": comment_doc.get("edited", False),
            "parent_comment_id": comment_doc.get("parent_comment_id"),
            "author_username": user.get("username"),
            "author_first_name": user.get("first_name"),
            "author_last_name": user.get("last_name")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Create comment error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create comment")


@app.get("/api/tasks/{task_id}/comments", response_model=List[CommentResponse])
async def get_task_comments(task_id: str):
    """Get all comments for a task"""
    try:
        # Verify task exists
        task = await asyncio.to_thread(tasks_collection.find_one, {"_id": ObjectId(task_id)})
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Get comments
        comment_docs = await asyncio.to_thread(
            lambda: list(comments_collection.find({"task_id": task_id}).sort("created_at", 1))
        )
        
        comments_list = []
        for doc in comment_docs:
            # Get author info
            author = await asyncio.to_thread(
                users_collection.find_one,
                {"_id": ObjectId(doc["user_id"])}
            )
            
            comments_list.append({
                "id": str(doc["_id"]),
                "task_id": doc["task_id"],
                "user_id": doc["user_id"],
                "content": doc["content"],
                "created_at": doc["created_at"],
                "updated_at": doc["updated_at"],
                "edited": doc.get("edited", False),
                "parent_comment_id": doc.get("parent_comment_id"),
                "author_username": author.get("username") if author else None,
                "author_first_name": author.get("first_name") if author else None,
                "author_last_name": author.get("last_name") if author else None
            })
        
        return comments_list
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get comments error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get comments")


@app.put("/api/comments/{comment_id}", response_model=CommentResponse)
async def update_comment(comment_id: str, comment_update: CommentUpdate, request: Request):
    """Update a comment"""
    try:
        # Get current user
        user = await get_current_user_from_token(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Check if comment exists
        comment = await asyncio.to_thread(comments_collection.find_one, {"_id": ObjectId(comment_id)})
        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")
        
        # Check if user is the author
        if str(user["_id"]) != comment["user_id"]:
            raise HTTPException(status_code=403, detail="Not authorized to edit this comment")
        
        # Update comment
        update_data = {
            "content": comment_update.content,
            "updated_at": datetime.utcnow(),
            "edited": True
        }
        
        await asyncio.to_thread(
            comments_collection.update_one,
            {"_id": ObjectId(comment_id)},
            {"$set": update_data}
        )
        
        updated_comment = await asyncio.to_thread(comments_collection.find_one, {"_id": ObjectId(comment_id)})
        
        return {
            "id": str(updated_comment["_id"]),
            "task_id": updated_comment["task_id"],
            "user_id": updated_comment["user_id"],
            "content": updated_comment["content"],
            "created_at": updated_comment["created_at"],
            "updated_at": updated_comment["updated_at"],
            "edited": updated_comment.get("edited", False),
            "parent_comment_id": updated_comment.get("parent_comment_id"),
            "author_username": user.get("username"),
            "author_first_name": user.get("first_name"),
            "author_last_name": user.get("last_name")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Update comment error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update comment")


@app.delete("/api/comments/{comment_id}", response_model=Message)
async def delete_comment(comment_id: str, request: Request):
    """Delete a comment"""
    try:
        # Get current user
        user = await get_current_user_from_token(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Check if comment exists
        comment = await asyncio.to_thread(comments_collection.find_one, {"_id": ObjectId(comment_id)})
        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")
        
        # Check if user is the author
        if str(user["_id"]) != comment["user_id"]:
            raise HTTPException(status_code=403, detail="Not authorized to delete this comment")
        
        # Delete comment
        result = await asyncio.to_thread(comments_collection.delete_one, {"_id": ObjectId(comment_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Comment not found")
        
        return {"message": "Comment deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Delete comment error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete comment")


# ============================================================================
# Phase 5: Subtasks Feature
# ============================================================================

@app.get("/api/tasks/{task_id}/subtasks", response_model=List[TaskResponse])
async def get_subtasks(task_id: str):
    """Get all subtasks of a task"""
    try:
        # Verify task exists
        task = await asyncio.to_thread(tasks_collection.find_one, {"_id": ObjectId(task_id)})
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Get subtasks
        subtasks = await asyncio.to_thread(
            lambda: list(tasks_collection.find({"parent_task_id": task_id}).sort("created_at", 1))
        )
        
        return [task_helper(subtask) for subtask in subtasks]
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get subtasks error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get subtasks")


# ============================================================================
# Phase 4: Enhanced Settings with History
# ============================================================================

@app.get("/api/users/{user_id}/settings/history", response_model=List[SettingsHistoryResponse])
async def get_settings_history(user_id: str):
    """Get settings change history"""
    try:
        # Get history
        history_docs = await asyncio.to_thread(
            lambda: list(settings_history_collection.find({"user_id": user_id}).sort("created_at", -1))
        )
        
        history_list = []
        for doc in history_docs:
            # Get username of who made the change
            changed_by_user = await asyncio.to_thread(
                users_collection.find_one,
                {"_id": ObjectId(doc.get("changed_by"))}
            )
            
            history_list.append({
                "id": str(doc["_id"]),
                "user_id": doc["user_id"],
                "settings": doc["settings"],
                "changed_by": doc["changed_by"],
                "created_at": doc["created_at"],
                "change_reason": doc.get("change_reason"),
                "changed_by_username": changed_by_user.get("username") if changed_by_user else None
            })
        
        return history_list
        
    except Exception as e:
        print(f"Get settings history error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get settings history")


@app.post("/api/users/{user_id}/settings/rollback", response_model=UserSettings)
async def rollback_settings(user_id: str, rollback_request: SettingsRollbackRequest, request: Request):
    """Rollback to a previous settings version"""
    try:
        # Get current user
        current_user = await get_current_user_from_token(request)
        if not current_user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Validate user exists
        user = await asyncio.to_thread(users_collection.find_one, {"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Find the historical settings
        history_doc = await asyncio.to_thread(
            settings_history_collection.find_one,
            {"_id": ObjectId(rollback_request.history_id), "user_id": user_id}
        )
        
        if not history_doc:
            raise HTTPException(status_code=404, detail="Settings history not found")
        
        old_settings = history_doc["settings"]
        
        # Update user's settings to the old values
        await asyncio.to_thread(users_collection.update_one, 
            {"_id": ObjectId(user_id)},
            {"$set": {"settings": old_settings, "updated_at": datetime.utcnow()}}
        )
        
        # Track this rollback as a new history entry
        rollback_entry = {
            "user_id": user_id,
            "settings": old_settings,
            "changed_by": str(current_user["_id"]),
            "created_at": datetime.utcnow(),
            "change_reason": f"Rolled back to settings from {history_doc['created_at']}"
        }
        await asyncio.to_thread(settings_history_collection.insert_one, rollback_entry)
        
        return old_settings
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Rollback settings error: {e}")
        raise HTTPException(status_code=500, detail="Failed to rollback settings")


# ============================================================================
# Phase 5: Task Attachments
# ============================================================================

@app.post("/api/tasks/{task_id}/attachments", response_model=TaskAttachmentResponse)
async def upload_task_attachment(task_id: str, file: UploadFile = File(...), description: Optional[str] = Form(None), request: Request = None):
    """Upload a file attachment to a task"""
    try:
        # Get current user
        user = await get_current_user_from_token(request) if request else None
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Verify task exists
        task = await asyncio.to_thread(tasks_collection.find_one, {"_id": ObjectId(task_id)})
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Create upload directory if it doesn't exist
        upload_dir = "static/uploads/tasks"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        import uuid
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        # Save file
        file_content = await file.read()
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Get file size
        file_size = len(file_content)
        
        # Create attachment record
        attachment_dict = {
            "task_id": task_id,
            "user_id": str(user["_id"]),
            "filename": file.filename,
            "file_path": file_path,
            "file_size": file_size,
            "file_type": file.content_type or "application/octet-stream",
            "uploaded_at": datetime.utcnow(),
            "description": description
        }
        
        result = await asyncio.to_thread(task_attachments_collection.insert_one, attachment_dict)
        attachment_doc = await asyncio.to_thread(task_attachments_collection.find_one, {"_id": result.inserted_id})
        
        return {
            "id": str(attachment_doc["_id"]),
            "task_id": attachment_doc["task_id"],
            "user_id": attachment_doc["user_id"],
            "filename": attachment_doc["filename"],
            "file_path": attachment_doc["file_path"],
            "file_size": attachment_doc["file_size"],
            "file_type": attachment_doc["file_type"],
            "uploaded_at": attachment_doc["uploaded_at"],
            "description": attachment_doc.get("description"),
            "uploader_username": user.get("username")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Upload attachment error: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload attachment")


@app.get("/api/tasks/{task_id}/attachments", response_model=List[TaskAttachmentResponse])
async def get_task_attachments(task_id: str):
    """Get all attachments for a task"""
    try:
        # Get attachments
        attachments = await asyncio.to_thread(
            lambda: list(task_attachments_collection.find({"task_id": task_id}).sort("uploaded_at", -1))
        )
        
        attachments_list = []
        for doc in attachments:
            # Get uploader info
            uploader = await asyncio.to_thread(
                users_collection.find_one,
                {"_id": ObjectId(doc["user_id"])}
            )
            
            attachments_list.append({
                "id": str(doc["_id"]),
                "task_id": doc["task_id"],
                "user_id": doc["user_id"],
                "filename": doc["filename"],
                "file_path": doc["file_path"],
                "file_size": doc["file_size"],
                "file_type": doc["file_type"],
                "uploaded_at": doc["uploaded_at"],
                "description": doc.get("description"),
                "uploader_username": uploader.get("username") if uploader else None
            })
        
        return attachments_list
        
    except Exception as e:
        print(f"Get attachments error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get attachments")


@app.get("/api/tasks/{task_id}/attachments/{attachment_id}/download")
async def download_task_attachment(task_id: str, attachment_id: str, request: Request):
    """Download a task attachment"""
    try:
        # Get current user
        user = await get_current_user_from_token(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Get attachment
        attachment = await asyncio.to_thread(
            task_attachments_collection.find_one,
            {"_id": ObjectId(attachment_id), "task_id": task_id}
        )
        
        if not attachment:
            raise HTTPException(status_code=404, detail="Attachment not found")
        
        # Check if file exists
        if not os.path.exists(attachment["file_path"]):
            raise HTTPException(status_code=404, detail="File not found")
        
        # Return file
        return FileResponse(
            path=attachment["file_path"],
            filename=attachment["filename"],
            media_type=attachment["file_type"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Download attachment error: {e}")
        raise HTTPException(status_code=500, detail="Failed to download attachment")


@app.delete("/api/tasks/attachments/{attachment_id}")
async def delete_task_attachment(attachment_id: str, request: Request):
    """Delete a task attachment"""
    try:
        # Get current user
        user = await get_current_user_from_token(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Get attachment
        attachment = await asyncio.to_thread(
            task_attachments_collection.find_one,
            {"_id": ObjectId(attachment_id)}
        )
        
        if not attachment:
            raise HTTPException(status_code=404, detail="Attachment not found")
        
        # Check if user owns the attachment
        if attachment["user_id"] != str(user["_id"]):
            raise HTTPException(status_code=403, detail="Not authorized to delete this attachment")
        
        # Delete file from filesystem
        if os.path.exists(attachment["file_path"]):
            os.remove(attachment["file_path"])
        
        # Delete attachment record
        result = await asyncio.to_thread(
            task_attachments_collection.delete_one,
            {"_id": ObjectId(attachment_id)}
        )
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Attachment not found")
        
        return {"message": "Attachment deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Delete attachment error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete attachment")


# ============================================================================
# Phase 5: Categories
# ============================================================================

@app.post("/api/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(category_data: CategoryCreate, request: Request):
    """Create a new category"""
    try:
        user = await get_current_user_from_token(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        category_dict = category_data.dict()
        category_dict["user_id"] = str(user["_id"])
        category_dict["created_at"] = datetime.utcnow()
        category_dict["task_count"] = 0
        
        result = await asyncio.to_thread(categories_collection.insert_one, category_dict)
        category_doc = await asyncio.to_thread(categories_collection.find_one, {"_id": result.inserted_id})
        
        return {
            "id": str(category_doc["_id"]),
            "user_id": category_doc["user_id"],
            "name": category_doc["name"],
            "description": category_doc.get("description"),
            "color": category_doc.get("color"),
            "icon": category_doc.get("icon"),
            "created_at": category_doc["created_at"],
            "task_count": category_doc.get("task_count", 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Create category error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create category")


@app.get("/api/users/{user_id}/categories", response_model=List[CategoryResponse])
async def get_user_categories(user_id: str):
    """Get all categories for a user"""
    try:
        categories = await asyncio.to_thread(
            lambda: list(categories_collection.find({"user_id": user_id}).sort("name", 1))
        )
        
        return [{
            "id": str(cat["_id"]),
            "user_id": cat["user_id"],
            "name": cat["name"],
            "description": cat.get("description"),
            "color": cat.get("color"),
            "icon": cat.get("icon"),
            "created_at": cat["created_at"],
            "task_count": cat.get("task_count", 0)
        } for cat in categories]
        
    except Exception as e:
        print(f"Get categories error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get categories")


# ============================================================================
# Phase 5: Task Templates
# ============================================================================

@app.post("/api/users/{user_id}/templates", response_model=TaskTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_task_template(user_id: str, template_data: TaskTemplateCreate):
    """Create a task template"""
    try:
        template_dict = template_data.dict()
        template_dict["user_id"] = user_id
        template_dict["created_at"] = datetime.utcnow()
        template_dict["updated_at"] = datetime.utcnow()
        
        result = await asyncio.to_thread(task_templates_collection.insert_one, template_dict)
        template_doc = await asyncio.to_thread(task_templates_collection.find_one, {"_id": result.inserted_id})
        
        return {
            "id": str(template_doc["_id"]),
            "user_id": template_doc["user_id"],
            "name": template_doc["name"],
            "title": template_doc["title"],
            "description": template_doc["description"],
            "default_priority": template_doc["default_priority"],
            "default_tags": template_doc.get("default_tags", []),
            "created_at": template_doc["created_at"],
            "updated_at": template_doc["updated_at"]
        }
        
    except Exception as e:
        print(f"Create template error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create template")


@app.get("/api/users/{user_id}/templates", response_model=List[TaskTemplateResponse])
async def get_user_templates(user_id: str):
    """Get all task templates for a user"""
    try:
        templates = await asyncio.to_thread(
            lambda: list(task_templates_collection.find({"user_id": user_id}).sort("name", 1))
        )
        
        return [{
            "id": str(t["_id"]),
            "user_id": t["user_id"],
            "name": t["name"],
            "title": t["title"],
            "description": t["description"],
            "default_priority": t["default_priority"],
            "default_tags": t.get("default_tags", []),
            "created_at": t["created_at"],
            "updated_at": t["updated_at"]
        } for t in templates]
        
    except Exception as e:
        print(f"Get templates error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get templates")


# ============================================================================
# Phase 5: Bulk Operations
# ============================================================================

@app.post("/api/tasks/bulk-update", response_model=Message)
async def bulk_update_tasks(task_ids: List[str], update_data: dict, request: Request):
    """Update multiple tasks at once"""
    try:
        user = await get_current_user_from_token(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Validate task IDs
        for task_id in task_ids:
            try:
                ObjectId(task_id)
            except:
                raise HTTPException(status_code=400, detail=f"Invalid task ID: {task_id}")
        
        # Update tasks
        update_data["updated_at"] = datetime.utcnow()
        result = await asyncio.to_thread(
            tasks_collection.update_many,
            {"_id": {"$in": [ObjectId(tid) for tid in task_ids]}},
            {"$set": update_data}
        )
        
        return {"message": f"Successfully updated {result.modified_count} tasks"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Bulk update error: {e}")
        raise HTTPException(status_code=500, detail="Failed to bulk update tasks")


@app.post("/api/tasks/bulk-delete", response_model=Message)
async def bulk_delete_tasks(task_ids: List[str], request: Request):
    """Delete multiple tasks at once"""
    try:
        user = await get_current_user_from_token(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Validate task IDs
        for task_id in task_ids:
            try:
                ObjectId(task_id)
            except:
                raise HTTPException(status_code=400, detail=f"Invalid task ID: {task_id}")
        
        # Delete tasks
        result = await asyncio.to_thread(
            tasks_collection.delete_many,
            {"_id": {"$in": [ObjectId(tid) for tid in task_ids]}}
        )
        
        return {"message": f"Successfully deleted {result.deleted_count} tasks"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Bulk delete error: {e}")
        raise HTTPException(status_code=500, detail="Failed to bulk delete tasks")


# Test endpoint for email validation
@app.post("/api/test/validate-email")
async def test_email_validation(email_data: dict):
    """Test endpoint to validate email format"""
    try:
        from database.schema import UserRegister
        # Create a test user object with minimal data
        test_user = UserRegister(
            username="testuser",
            first_name="Test",
            last_name="User", 
            email=email_data.get("email", ""),
            phone_number="+1234567890",
            password="TestPass123!"
        )
        return {"valid": True, "message": "Email format is valid", "normalized_email": test_user.email}
    except ValidationError as e:
        error_messages = []
        for error in e.errors():
            if 'email' in error['loc']:
                error_messages.append(error['msg'])
        return {"valid": False, "errors": error_messages}
    except Exception as e:
        return {"valid": False, "errors": [str(e)]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
