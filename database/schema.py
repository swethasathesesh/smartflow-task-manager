from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from database.models import TaskStatus, TaskPriority


# User Schemas
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    phone_number: str = Field(..., min_length=10, max_length=15)
    password: str = Field(..., min_length=6)

    class Config:
        json_schema_extra = {
            "example": {
                "username": "johndoe",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com",
                "phone_number": "+1234567890",
                "password": "securePassword123"
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
    bio: Optional[str] = None

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


# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class Message(BaseModel):
    message: str

