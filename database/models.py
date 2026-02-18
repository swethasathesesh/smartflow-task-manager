from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class User(BaseModel):
    username: str
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: str
    password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    profile_image: Optional[str] = None
    bio: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "username": "johndoe",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com",
                "phone_number": "+1234567890",
                "password": "securePassword123",
                "bio": "Software Developer"
            }
        }


class Task(BaseModel):
    title: str
    description: str
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    user_id: str
    due_date: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    tags: Optional[list[str]] = []
    assigned_to: Optional[str] = None
    notes: Optional[str] = None
    parent_task_id: Optional[str] = None  # For subtasks
    category_id: Optional[str] = None  # Link to category/project
    depends_on: Optional[list[str]] = []  # List of task_ids this task depends on
    is_recurring: bool = False  # Whether task is recurring
    recurrence_pattern: Optional[str] = None  # daily, weekly, monthly, etc.
    next_occurrence: Optional[datetime] = None  # When to create next instance
    estimated_time: Optional[int] = None  # Estimated time in minutes
    actual_time: Optional[int] = None  # Actual time spent in minutes

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Complete project documentation",
                "description": "Write comprehensive documentation for the task management system",
                "status": "todo",
                "priority": "high",
                "user_id": "user123",
                "due_date": "2025-10-20T23:59:59",
                "start_time": "2025-10-16T09:00:00",
                "tags": ["documentation", "project"],
                "notes": "Include API documentation and user guide",
                "parent_task_id": None
            }
        }


class PasswordResetToken(BaseModel):
    """Model for password reset tokens"""
    email: EmailStr
    token: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    used: bool = False


class TaskHistory(BaseModel):
    """Model for tracking task change history"""
    task_id: str
    user_id: str
    field_name: str  # Which field was changed
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    changed_by: str  # User ID of who made the change
    created_at: datetime = Field(default_factory=datetime.utcnow)
    comment: Optional[str] = None  # Optional description of the change


class Comment(BaseModel):
    """Model for task comments"""
    task_id: str
    user_id: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    edited: bool = False
    parent_comment_id: Optional[str] = None  # For nested replies


class SettingsHistory(BaseModel):
    """Model for tracking settings changes"""
    user_id: str
    settings: dict  # The settings values
    changed_by: str  # User ID of who made the change
    created_at: datetime = Field(default_factory=datetime.utcnow)
    change_reason: Optional[str] = None  # Optional description of why settings were changed


class TaskAttachment(BaseModel):
    """Model for task file attachments"""
    task_id: str
    user_id: str
    filename: str
    file_path: str  # Path to the file on server
    file_size: int  # Size in bytes
    file_type: str  # MIME type
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    description: Optional[str] = None


class TaskTemplate(BaseModel):
    """Model for task templates"""
    user_id: str
    name: str
    title: str
    description: str
    default_priority: TaskPriority = TaskPriority.MEDIUM
    default_tags: Optional[list[str]] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Category(BaseModel):
    """Model for task categories/projects"""
    user_id: str
    name: str
    description: Optional[str] = None
    color: Optional[str] = "#007bff"  # Color code for the category
    icon: Optional[str] = None  # Icon name
    created_at: datetime = Field(default_factory=datetime.utcnow)
    task_count: int = 0  # Number of tasks in this category

