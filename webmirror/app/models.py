"""
Data models
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Item(BaseModel):
    id: Optional[int] = None
    name: str
    created_at: datetime = datetime.now()