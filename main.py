import random
import string
import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, status, Depends, UploadFile, File, Response, Query, Form, Header
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
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
    ProfilePictureResponse, PasswordChange, UserSettings
)
from database.models import TaskStatus
from config import users_collection, tasks_collection
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
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://localhost:3000").split(",")

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
        "notes": task.get("notes")
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
async def update_user_settings(user_id: str, settings: UserSettings):
    """Update user settings"""
    try:
        # Validate user exists
        user = await asyncio.to_thread(users_collection.find_one, {"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update settings
        settings_dict = settings.dict()
        await asyncio.to_thread(users_collection.update_one, 
            {"_id": ObjectId(user_id)},
            {"$set": {"settings": settings_dict, "updated_at": datetime.utcnow()}}
        )
        
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
async def update_task(task_id: str, task_update: TaskUpdate):
    """Update a task"""
    try:
        # Get current task to check existing values
        current_task = await asyncio.to_thread(tasks_collection.find_one, {"_id": ObjectId(task_id)})
        if not current_task:
            raise HTTPException(status_code=404, detail="Task not found")
        
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
