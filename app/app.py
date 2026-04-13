from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from bson import ObjectId
from typing import Optional
from datetime import datetime, timedelta

from app.database import users_collection, tasks_collection, ping_server
from app.utils import hash_password, verify_password, create_access_token, verify_token
from app.schemas import UserCreate, UserResponse

class LoginRequest(BaseModel):
    email: str
    password: str

class TaskCreate(BaseModel):
    title: str
    description: str = ""
    due_date: Optional[str] = None
    priority: str = "Medium" # <-- NEW: Storing priority

class TimeUpdate(BaseModel):
    time_spent: int

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/template")

@app.on_event("startup")
async def startup_db_client():
    await ping_server()

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login_page.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def load_dashboard(request: Request):
    token = request.cookies.get("access_token")
    payload = verify_token(token) if token else None
    if not payload: return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("dashboard.html", {"request": request, "user_name": payload.get("name")})

@app.get("/logout")
async def logout_user():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("access_token")
    return response

@app.post("/signup", response_model=UserResponse)
async def register_user(user: UserCreate):
    user_dict = user.model_dump()
    user_dict["password"] = hash_password(user.password)
    await users_collection.insert_one(user_dict)
    return user

@app.post("/login")
async def login_user(request: LoginRequest):
    user = await users_collection.find_one({"email": request.email})
    if not user or not verify_password(request.password, user["password"]):
        raise HTTPException(status_code=400, detail="Invalid email or password")
    token = create_access_token({"email": user["email"], "name": user["full_name"]})
    response = JSONResponse(content={"message": "Login successful!"})
    response.set_cookie(key="access_token", value=token, httponly=True)
    return response

@app.post("/api/tasks")
async def create_task(task: TaskCreate, request: Request):
    token = request.cookies.get("access_token")
    payload = verify_token(token)
    if not payload: raise HTTPException(status_code=401)
    new_task = {
        "user_email": payload.get("email"),
        "title": task.title,
        "description": task.description,
        "due_date": task.due_date,
        "priority": task.priority, # <-- Saving priority
        "time_spent": 0,
        "status": "pending",
        "created_at": datetime.utcnow()
    }
    await tasks_collection.insert_one(new_task)
    return {"message": "Created"}

@app.get("/api/tasks")
async def get_tasks(request: Request):
    token = request.cookies.get("access_token")
    payload = verify_token(token)
    if not payload: raise HTTPException(status_code=401)
    tasks = await tasks_collection.find({"user_email": payload.get("email")}).sort("due_date", 1).to_list(100)
    for t in tasks: t["_id"] = str(t["_id"])
    return tasks

@app.put("/api/tasks/{task_id}")
async def complete_task(task_id: str):
    await tasks_collection.update_one({"_id": ObjectId(task_id)}, {"$set": {"status": "completed", "completed_at": datetime.utcnow()}})
    return {"message": "Done"}

@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    await tasks_collection.delete_one({"_id": ObjectId(task_id)})
    return {"message": "Deleted"}

@app.put("/api/tasks/{task_id}/time")
async def update_task_time(task_id: str, data: TimeUpdate):
    await tasks_collection.update_one({"_id": ObjectId(task_id)}, {"$set": {"time_spent": data.time_spent}})
    return {"message": "Saved"}

@app.get("/api/analysis")
async def get_analysis(request: Request):
    token = request.cookies.get("access_token")
    payload = verify_token(token)
    if not payload: raise HTTPException(status_code=401)
    
    last_7_days = {}
    total_seconds_today = 0
    today_str = datetime.utcnow().strftime("%Y-%m-%d")

    for i in range(7):
        date = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
        last_7_days[date] = 0
        
    tasks = await tasks_collection.find({
        "user_email": payload.get("email"),
        "status": "completed",
        "completed_at": {"$gte": datetime.utcnow() - timedelta(days=7)}
    }).to_list(100)
    
    for t in tasks:
        d = t["completed_at"].strftime("%Y-%m-%d")
        if d in last_7_days: last_7_days[d] += 1
        if d == today_str: total_seconds_today += t.get("time_spent", 0)
            
    return {"chart_data": last_7_days, "total_seconds_today": total_seconds_today}