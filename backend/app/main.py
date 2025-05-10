"""
Simplified FastAPI app with only authentication endpoints and basic file upload
"""

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session
import traceback
import os
import uuid
import logging
import sys

# Import database functions
from .database import init_db, get_session, get_engine, create_engine
from .auth import authenticate_user, create_access_token, get_current_user
from .models import User

# Import routers
from .routers import handwriting, results, extract, jobs, auth, upload

# Setup logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("backend.log")
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="DocTranscribe API", version="0.2.0")

# Add CORS middleware to allow requests from frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["Content-Disposition", "Content-Type", "Content-Length"],
)

# In-memory state for application
memory_state = {
    "sample_job_id": None
}

# Global exception handler - ensures the server never crashes on requests
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Exception occurred: {str(exc)}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"error": f"Internal server error: {str(exc)}"},
    )

# Create uploads directory
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Create error_pdfs directory for failed processing
ERROR_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "error_pdfs")
os.makedirs(ERROR_DIR, exist_ok=True)

# Create excel_exports directory for generated XLSX files
EXCEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "excel_exports")
os.makedirs(EXCEL_DIR, exist_ok=True)

# Mount uploads directory for static file serving
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialization on application startup."""
    logger.info("Ensuring database schema is up-to-date...")
    try:
        # Ensure the path to recreate_db.py is correct
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if backend_dir not in sys.path:
            sys.path.append(backend_dir)
        
        # 1. Recreate (deletes file if exists, then creates tables with a temporary engine)
        from recreate_db import recreate_database
        recreate_database()
        logger.info("Database file recreated successfully.")
        
        # 2. Re-initialize the main application engine *after* recreating the file
        # This ensures the main engine connects to the *new* file
        global engine # Need to modify the global engine instance
        # Close existing engine connections if possible (though recreating often handles this)
        # If using a connection pool, you might need engine.dispose()
        
        # Create a *new* engine instance for the application to use
        app.state.engine = create_engine() # Use the factory function from database.py
        engine = app.state.engine # Update the global engine reference if needed elsewhere
        logger.info("Main application database engine re-initialized.")

        # 3. Initialize DB content (adds admin user etc.) using the new engine
        init_db() 
        logger.info("Database content initialized successfully after recreation.")
        
    except Exception as e:
        logger.error(f"CRITICAL ERROR during database setup: {str(e)}")
        logger.error(traceback.format_exc())
    
    # Initialize in-memory state
    logger.info("Initializing in-memory state...")
    with Session(get_engine()): # Use get_engine() to ensure it uses the latest engine
        sample_job_id = str(uuid.uuid4())
        memory_state["sample_job_id"] = sample_job_id
    
    logger.info("Application startup complete")

# Include routers
app.include_router(handwriting.router)
app.include_router(results.router)
app.include_router(extract.router)
app.include_router(jobs.router)
app.include_router(auth.router)
app.include_router(upload.router)

# Auth endpoints
@app.post("/auth/login")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_session)
):
    """Authenticate user and return JWT token."""
    logger.info(f"Login attempt for user: {form_data.username}")
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create and return token
    access_token = create_access_token(
        data={"sub": user.email, "user_id": str(user.id)}
    )
    
    logger.info(f"Login successful for user: {user.email}")
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat()
        }
    }

@app.get("/auth/me")
async def get_user_me(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "model": "gpt-4.1", "version": "1.0.0"}

@app.get("/debug-state")
async def debug_state(request: Request):
    """Debug endpoint to see application state (in development only)."""
    if os.environ.get("ENV") == "production":
        raise HTTPException(status_code=404, detail="Not found")
    
    # Return a safe copy of app state for debugging
    state = {}
    if hasattr(request.app.state, "jobs"):
        state["jobs"] = request.app.state.jobs
    else:
        state["jobs"] = []
    
    if hasattr(request.app.state, "batch_jobs"):
        state["batch_jobs"] = request.app.state.batch_jobs
    else:
        state["batch_jobs"] = []
    
    return {"app_state": state} 

# Make sure get_engine returns the potentially updated engine
from .database import get_engine as db_get_engine
def get_engine():
    return app.state.engine if hasattr(app.state, 'engine') else db_get_engine() 