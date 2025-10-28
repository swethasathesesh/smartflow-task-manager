from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
import re
from database.models import TaskStatus, TaskPriority


# User Schemas
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    phone_number: str = Field(..., min_length=10, max_length=15)
    password: str = Field(..., min_length=6)

    @validator('email')
    def validate_email(cls, v):
        """Enhanced email validation"""
        email_str = str(v).lower().strip()
        
        # Check for common invalid patterns
        if '..' in email_str:
            raise ValueError('Email cannot contain consecutive dots')
        
        if email_str.startswith('.') or email_str.endswith('.'):
            raise ValueError('Email cannot start or end with a dot')
        
        # Check for valid email pattern
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email_str):
            raise ValueError('Invalid email format')
        
        # Check for common disposable email domains (optional)
        disposable_domains = [
            '10minutemail.com', 'tempmail.org', 'guerrillamail.com',
            'mailinator.com', 'throwaway.email', 'temp-mail.org'
        ]
        domain = email_str.split('@')[1]
        if domain in disposable_domains:
            raise ValueError('Disposable email addresses are not allowed')
        
        return email_str

    @validator('username')
    def validate_username(cls, v):
        """Username validation"""
        username = v.strip()
        
        # Check for valid characters (alphanumeric, underscore, hyphen)
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            raise ValueError('Username can only contain letters, numbers, underscores, and hyphens')
        
        # Check if username starts with a letter
        if not username[0].isalpha():
            raise ValueError('Username must start with a letter')
        
        return username.lower()

    @validator('password')
    def validate_password(cls, v):
        """Enhanced password validation"""
        password = v.strip()
        
        if len(password) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', password):
            raise ValueError('Password must contain at least one uppercase letter')
        
        # Check for at least one lowercase letter
        if not re.search(r'[a-z]', password):
            raise ValueError('Password must contain at least one lowercase letter')
        
        # Check for at least one digit
        if not re.search(r'\d', password):
            raise ValueError('Password must contain at least one number')
        
        # Check for at least one special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValueError('Password must contain at least one special character (!@#$%^&*(),.?":{}|<>)')
        
        return password

    @validator('phone_number')
    def validate_phone_number(cls, v):
        """Phone number validation"""
        phone = v.strip()
        
        # Remove common formatting characters
        phone_clean = re.sub(r'[^\d+]', '', phone)
        
        # Check for valid phone number pattern
        if not re.match(r'^\+?[1-9]\d{1,14}$', phone_clean):
            raise ValueError('Invalid phone number format')
        
        return phone_clean

    class Config:
        json_schema_extra = {
            "example": {
                "username": "johndoe",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com",
                "phone_number": "+1234567890",
                "password": "SecurePass123!"
            }
        }


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "john.doe@example.com",
                "password": "securePassword123"
            }
        }


class UserResponse(BaseModel):
    id: str
    username: str
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: str
    created_at: datetime
    profile_image: Optional[str] = None
    profile_thumbnail: Optional[str] = None
    bio: Optional[str] = None
    settings: Optional[dict] = None
    email_verified: Optional[bool] = None
    is_active: Optional[bool] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "username": "johndoe",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com",
                "phone_number": "+1234567890",
                "created_at": "2025-10-16T10:00:00",
                "bio": "Software Developer"
            }
        }


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    bio: Optional[str] = None
    profile_image: Optional[str] = None
    
    @validator('phone_number')
    def validate_phone_number(cls, v):
        """Phone number validation"""
        if v is None:
            return v
        phone = v.strip()
        phone_clean = re.sub(r'[^\d+]', '', phone)
        if not re.match(r'^\+?[1-9]\d{1,14}$', phone_clean):
            raise ValueError('Invalid phone number format')
        return phone_clean


class ProfilePictureResponse(BaseModel):
    success: bool
    message: str
    file_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    original_filename: Optional[str] = None


# Task Schemas
class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    tags: Optional[list[str]] = []
    assigned_to: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Complete project documentation",
                "description": "Write comprehensive documentation for the task management system",
                "status": "todo",
                "priority": "high",
                "due_date": "2025-10-20T23:59:59",
                "start_time": "2025-10-16T09:00:00",
                "tags": ["documentation", "project"],
                "notes": "Include API documentation and user guide"
            }
        }


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    tags: Optional[list[str]] = None
    assigned_to: Optional[str] = None
    notes: Optional[str] = None


class TaskResponse(BaseModel):
    id: str
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    user_id: str
    due_date: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    tags: Optional[list[str]] = []
    assigned_to: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "title": "Complete project documentation",
                "description": "Write comprehensive documentation for the task management system",
                "status": "todo",
                "priority": "high",
                "user_id": "user123",
                "due_date": "2025-10-20T23:59:59",
                "start_time": "2025-10-16T09:00:00",
                "created_at": "2025-10-16T10:00:00",
                "updated_at": "2025-10-16T10:00:00",
                "tags": ["documentation", "project"],
                "notes": "Include API documentation and user guide"
            }
        }


# OTP Schemas
class OTPRequest(BaseModel):
    email: EmailStr
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com"
            }
        }


class OTPVerification(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)
    
    @validator('otp')
    def validate_otp(cls, v):
        """Validate OTP format"""
        otp = v.strip()
        if not otp.isdigit():
            raise ValueError('OTP must contain only digits')
        return otp
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "otp": "123456"
            }
        }


class PreRegistrationUser(BaseModel):
    """User data for pre-registration (before OTP verification)"""
    username: str = Field(..., min_length=3, max_length=50)
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    phone_number: str = Field(..., min_length=10, max_length=15)
    password: str = Field(..., min_length=6)
    
    # Use the same validators as UserRegister
    @validator('email')
    def validate_email(cls, v):
        """Enhanced email validation"""
        email_str = str(v).lower().strip()
        
        if '..' in email_str:
            raise ValueError('Email cannot contain consecutive dots')
        
        if email_str.startswith('.') or email_str.endswith('.'):
            raise ValueError('Email cannot start or end with a dot')
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email_str):
            raise ValueError('Invalid email format')
        
        disposable_domains = [
            '10minutemail.com', 'tempmail.org', 'guerrillamail.com',
            'mailinator.com', 'throwaway.email', 'temp-mail.org'
        ]
        domain = email_str.split('@')[1]
        if domain in disposable_domains:
            raise ValueError('Disposable email addresses are not allowed')
        
        return email_str

    @validator('username')
    def validate_username(cls, v):
        username = v.strip()
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            raise ValueError('Username can only contain letters, numbers, underscores, and hyphens')
        if not username[0].isalpha():
            raise ValueError('Username must start with a letter')
        return username.lower()

    @validator('password')
    def validate_password(cls, v):
        password = v.strip()
        if len(password) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', password):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', password):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', password):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValueError('Password must contain at least one special character (!@#$%^&*(),.?":{}|<>)')
        return password

    @validator('phone_number')
    def validate_phone_number(cls, v):
        phone = v.strip()
        phone_clean = re.sub(r'[^\d+]', '', phone)
        if not re.match(r'^\+?[1-9]\d{1,14}$', phone_clean):
            raise ValueError('Invalid phone number format')
        return phone_clean

    class Config:
        json_schema_extra = {
            "example": {
                "username": "johndoe",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com",
                "phone_number": "+1234567890",
                "password": "SecurePass123!"
            }
        }


class RegistrationWithOTP(BaseModel):
    """Registration request with OTP verification"""
    user_data: PreRegistrationUser
    otp: str = Field(..., min_length=6, max_length=6)
    
    @validator('otp')
    def validate_otp(cls, v):
        """Validate OTP format"""
        otp = v.strip()
        if not otp.isdigit():
            raise ValueError('OTP must contain only digits')
        return otp
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_data": {
                    "username": "johndoe",
                    "first_name": "John",
                    "last_name": "Doe",
                    "email": "john.doe@example.com",
                    "phone_number": "+1234567890",
                    "password": "SecurePass123!"
                },
                "otp": "123456"
            }
        }


# User Settings Schemas
class UserSettings(BaseModel):
    """User preferences and settings"""
    theme: str = Field(default="light", description="UI theme: light, dark, or auto")
    email_notifications: bool = Field(default=True, description="Enable email notifications")
    push_notifications: bool = Field(default=False, description="Enable push notifications")
    task_reminders: bool = Field(default=True, description="Enable task reminders")
    tasks_per_page: int = Field(default=25, description="Number of tasks per page")
    auto_save: bool = Field(default=True, description="Auto-save task changes")
    show_completed_tasks: bool = Field(default=True, description="Show completed tasks by default")
    profile_visibility: bool = Field(default=True, description="Public profile visibility")
    activity_tracking: bool = Field(default=False, description="Track user activity")
    session_timeout: int = Field(default=60, description="Session timeout in minutes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "theme": "light",
                "email_notifications": True,
                "push_notifications": False,
                "task_reminders": True,
                "tasks_per_page": 25,
                "auto_save": True,
                "show_completed_tasks": True,
                "profile_visibility": True,
                "activity_tracking": False,
                "session_timeout": 60
            }
        }


# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None
    user: UserResponse


class Message(BaseModel):
    message: str


class OTPResponse(BaseModel):
    success: bool
    message: str


class PasswordChange(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6)
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """Password validation for new password"""
        password = v.strip()
        
        if len(password) < 6:
            raise ValueError('Password must be at least 6 characters long')
        
        return password
    
    class Config:
        json_schema_extra = {
            "example": {
                "current_password": "oldPassword123",
                "new_password": "newSecurePassword456"
            }
        }

