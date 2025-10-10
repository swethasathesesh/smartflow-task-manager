from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .config import settings
from .database import connect_to_mongo, close_mongo_connection

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.API_DEBUG,
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Connect to MongoDB on startup"""
    await connect_to_mongo()

@app.on_event("shutdown")
async def shutdown_event():
    """Close MongoDB connection on shutdown"""
    await close_mongo_connection()

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Welcome to Task Management System API", "status": "running"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": settings.APP_NAME}

@app.get("/api/v1/")
async def api_info():
    """API information endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }

# Import and include routers
# from .auth.routes import router as auth_router
# from .users.routes import router as users_router
# from .tasks.routes import router as tasks_router

# app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
# app.include_router(users_router, prefix="/api/users", tags=["Users"])
# app.include_router(tasks_router, prefix="/api/tasks", tags=["Tasks"])

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.API_DEBUG,
        log_level="info"
    )
