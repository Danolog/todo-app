from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import List, Optional
import uuid

from . import models
from .database import SessionLocal, engine

# Create tables if they don't exist
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

from fastapi.responses import FileResponse

app.mount("/static", StaticFiles(directory="todo_app/static"), name="static")
templates = Jinja2Templates(directory="todo_app/templates")

@app.on_event("startup")
async def startup_db_client():
    # Simple migration to add owner_id if missing
    with engine.connect() as conn:
        try:
            conn.execute(text("SELECT owner_id FROM tasks LIMIT 1"))
        except Exception:
            # Column likely missing
            try:
                # SQLite syntax
                conn.execute(text("ALTER TABLE tasks ADD COLUMN owner_id VARCHAR"))
                conn.commit() # Commit the DDL change
                print("Migrated: Added owner_id column (SQLite)")
            except Exception:
                pass # Already exists or different DB handling

@app.get("/sw.js")
async def service_worker():
    return FileResponse("todo_app/static/sw.js", media_type="application/javascript")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(request: Request):
    user_id = request.cookies.get("user_id")
    if not user_id:
        user_id = str(uuid.uuid4())
    return user_id

class TaskCreate(BaseModel):
    title: str

class TaskResponse(BaseModel):
    id: int
    title: str
    is_complete: bool
    owner_id: Optional[str] = None

    class Config:
        from_attributes = True

@app.get("/")
def read_root(request: Request, db: Session = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    # If no cookie, we generate one in the response
    if not user_id:
        user_id = str(uuid.uuid4())
        response = templates.TemplateResponse("index.html", {"request": request, "tasks": []})
        response.set_cookie(key="user_id", value=user_id, max_age=31536000) # 1 year
        return response
    
    tasks = db.query(models.Task).filter(
        (models.Task.owner_id == user_id) | (models.Task.owner_id == None)
    ).all()
    # Note: owner_id==None allows seeing old tasks, or we can hide them. 
    # Let's hide them for strict isolation, or allow adoption. 
    # For simplicity: strict isolation for new users, but let's show NULLs for legacy (User 2 option)
    
    return templates.TemplateResponse("index.html", {"request": request, "tasks": tasks})

@app.get("/api/tasks", response_model=List[TaskResponse])
def get_tasks(db: Session = Depends(get_db), user_id: str = Depends(get_current_user)):
    return db.query(models.Task).filter(
        (models.Task.owner_id == user_id) | (models.Task.owner_id == None)
    ).all()

@app.post("/api/tasks", response_model=TaskResponse)
def create_task(task: TaskCreate, response: Response, db: Session = Depends(get_db), user_id: str = Depends(get_current_user)):
    # Ensure cookie is set if it was generated in dependency
    response.set_cookie(key="user_id", value=user_id, max_age=31536000)
    
    db_task = models.Task(title=task.title, owner_id=user_id)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@app.put("/api/tasks/{task_id}", response_model=TaskResponse)
def toggle_task(task_id: int, db: Session = Depends(get_db), user_id: str = Depends(get_current_user)):
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Allow if owner matches OR if owner is None (legacy task)
    if db_task.owner_id and db_task.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    db_task.is_complete = not db_task.is_complete
    
    # Claim ownership of legacy task on interaction? optional. Let's start with just allowing.
    if not db_task.owner_id:
        db_task.owner_id = user_id
        
    db.commit()
    db.refresh(db_task)
    return db_task

@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db), user_id: str = Depends(get_current_user)):
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if db_task.owner_id and db_task.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    db.delete(db_task)
    db.commit()
    return {"ok": True}
