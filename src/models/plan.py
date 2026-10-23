"""
Pydantic schemas for content planning and ideas.
"""
from typing import List, Optional
from pydantic import BaseModel


class TopicImportItem(BaseModel):
    baslik: Optional[str] = None
    title: Optional[str] = None
    konu: Optional[str] = None
    topic: Optional[str] = None
    name: Optional[str] = None
    
    yonergeler: Optional[str] = None
    instructions: Optional[str] = None
    yönerge: Optional[str] = None
    instruction: Optional[str] = None
    description: Optional[str] = None


class ImportTopicsRequest(BaseModel):
    topics: List[TopicImportItem]


class PlanRequest(BaseModel):
    count: int = 10


class IdeaItem(BaseModel):
    title: str
    topic: str
    description: Optional[str] = None


class ScrapedIdeasPayload(BaseModel):
    ideas: List[IdeaItem]


class UpdateMusicPayload(BaseModel):
    secilen_muzik: str
