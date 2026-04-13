# --- ALL IMPORTS AT THE TOP ---
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# Notice we added tasks_collection here!
from app.database import users_collection, tasks_collection, ping_server
from app.utils import hash_password, verify_password, create_access_token, verify_token
from app.schemas import UserCreate, UserResponse

# --- BLUEPRINTS (SCHEMAS) ---
class LoginRequest(BaseModel):
    email: str
    password: str

class TaskCreate(BaseModel):
    title: str
    description: str

# --- APP SETUP ---
app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/template")

@app.on_event("startup")
async def startup_db_client():
    await ping_server()

# --- FRONTEND PAGES (HTML) ---
@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login_page.html", {"request": request})

@app.get("/user", response_class=HTMLResponse)
async def user_page(request: Request):
    return templates.TemplateResponse("user_page.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def load_dashboard(request: Request):
    token = request.cookies.get("access_token")
    payload = None
    if token:
        payload = verify_token(token)
        
    if not payload:
        return RedirectResponse(url="/", status_code=303)
        
    user_name = payload.get("name")
    return templates.TemplateResponse("dashboard.html", {"request": request, "user_name": user_name})

@app.get("/logout")
async def logout_user():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("access_token")
    return response

# --- BACKEND API (DATA) ---
@app.post("/signup", response_model=UserResponse)
async def register_user(user: UserCreate):
    hashed_pw = hash_password(user.password)
    user_dict = user.model_dump()
    user_dict["password"] = hashed_pw
    await users_collection.insert_one(user_dict)
    return user

@app.post("/login")
async def login_user(request: LoginRequest):
    user = await users_collection.find_one({"email": request.email})
    if not user or not verify_password(request.password, user["password"]):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    token_data = {"email": user["email"], "name": user["full_name"]}
    token = create_access_token(token_data)

    response = JSONResponse(content={"message": "Login successful!"})
    response.set_cookie(key="access_token", value=token, httponly=True)
    return response

# --- NEW: TASK ENGINE ---
@app.post("/api/tasks")
async def create_task(task: TaskCreate, request: Request):
    token = request.cookies.get("access_token")
    if not token: raise HTTPException(status_code=401, detail="Not authenticated")
    payload = verify_token(token)
    if not payload: raise HTTPException(status_code=401, detail="Invalid token")

    user_email = payload.get("email")
    new_task = {
        "user_email": user_email,
        "title": task.title,
        "description": task.description,
        "status": "pending"
    }
    await tasks_collection.insert_one(new_task)
    return {"message": "Task created successfully!"}

@app.get("/api/tasks")
async def get_tasks(request: Request):
    token = request.cookies.get("access_token")
    if not token: raise HTTPException(status_code=401, detail="Not authenticated")
    payload = verify_token(token)
    if not payload: raise HTTPException(status_code=401, detail="Invalid token")

    user_email = payload.get("email")
    tasks_cursor = tasks_collection.find({"user_email": user_email})
    tasks = await tasks_cursor.to_list(length=100) 
    
    # Convert MongoDB IDs to normal text
    for task in tasks:
        task["_id"] = str(task["_id"])
        
    return tasks