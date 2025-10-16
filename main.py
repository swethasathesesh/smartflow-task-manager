from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.requests import Request
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import List, Optional
from bson import ObjectId
import bcrypt

from database.schema import (
    UserRegister, UserLogin, UserResponse, UserUpdate,
    TaskCreate, TaskUpdate, TaskResponse, Token, Message
)
from database.models import TaskStatus
from config import users_collection, tasks_collection

app = FastAPI(title="Task Management System", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        "bio": user.get("bio")
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


# API Routes - Authentication
@app.post("/api/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserRegister):
    """Register a new user"""
    # Check if user already exists
    existing_user = users_collection.find_one({"$or": [{"email": user.email}, {"username": user.username}]})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists"
        )
    
    # Create new user
    user_dict = user.dict()
    user_dict["password"] = hash_password(user.password)
    user_dict["created_at"] = datetime.utcnow()
    user_dict["updated_at"] = datetime.utcnow()
    
    result = users_collection.insert_one(user_dict)
    new_user = users_collection.find_one({"_id": result.inserted_id})
    
    return user_helper(new_user)


@app.post("/api/auth/login", response_model=Token)
async def login_user(user: UserLogin):
    """Login a user"""
    # Find user by email
    db_user = users_collection.find_one({"email": user.email})
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
    
    # Return token (simplified - in production, use JWT)
    return {
        "access_token": str(db_user["_id"]),
        "token_type": "bearer",
        "user": user_helper(db_user)
    }


# API Routes - Users
@app.get("/api/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """Get user by ID"""
    try:
        user = users_collection.find_one({"_id": ObjectId(user_id)})
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
        
        result = users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        updated_user = users_collection.find_one({"_id": ObjectId(user_id)})
        return user_helper(updated_user)
    except HTTPException:
        raise
    except:
        raise HTTPException(status_code=400, detail="Invalid user ID")


# API Routes - Tasks
@app.post("/api/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(task: TaskCreate, user_id: str):
    """Create a new task"""
    task_dict = task.dict()
    task_dict["user_id"] = user_id
    task_dict["created_at"] = datetime.utcnow()
    task_dict["updated_at"] = datetime.utcnow()
    
    result = tasks_collection.insert_one(task_dict)
    new_task = tasks_collection.find_one({"_id": result.inserted_id})
    
    return task_helper(new_task)


@app.get("/api/tasks", response_model=List[TaskResponse])
async def get_tasks(user_id: str, status: Optional[TaskStatus] = None):
    """Get all tasks for a user, optionally filtered by status"""
    query = {"user_id": user_id}
    if status:
        query["status"] = status
    
    tasks = list(tasks_collection.find(query).sort("created_at", -1))
    return [task_helper(task) for task in tasks]


@app.get("/api/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """Get a specific task by ID"""
    try:
        task = tasks_collection.find_one({"_id": ObjectId(task_id)})
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
        update_data = {k: v for k, v in task_update.dict().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="No data to update")
        
        update_data["updated_at"] = datetime.utcnow()
        
        result = tasks_collection.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Task not found")
        
        updated_task = tasks_collection.find_one({"_id": ObjectId(task_id)})
        return task_helper(updated_task)
    except HTTPException:
        raise
    except:
        raise HTTPException(status_code=400, detail="Invalid task ID")


@app.delete("/api/tasks/{task_id}", response_model=Message)
async def delete_task(task_id: str):
    """Delete a task"""
    try:
        result = tasks_collection.delete_one({"_id": ObjectId(task_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"message": "Task deleted successfully"}
    except HTTPException:
        raise
    except:
        raise HTTPException(status_code=400, detail="Invalid task ID")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
