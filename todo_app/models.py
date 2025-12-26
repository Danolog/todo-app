from sqlalchemy import Boolean, Column, Integer, String
from .database import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    is_complete = Column(Boolean, default=False)
    owner_id = Column(String, index=True, nullable=True)
