from pydantic import BaseModel, Field
from typing import List
from app.schemas.common import TaskPriority

class Task(BaseModel):
    id: str = Field(...)
    title: str = Field(...)
    description: str = Field(...)
    target_files: List[str] = Field(default_factory=list)
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    dependencies: List[str] = Field(default_factory=list)

class Plan(BaseModel):
    tasks: List[Task] = Field(...)
