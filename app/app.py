from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

# Tell FastAPI where your CSS/JS/Images are
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Tell FastAPI where your HTML files are (folder is 'template')
templates = Jinja2Templates(directory="app/template")

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login_page.html", {"request": request})

@app.get("/user", response_class=HTMLResponse)
async def user_page(request: Request):
    return templates.TemplateResponse("user_page.html", {"request": request})