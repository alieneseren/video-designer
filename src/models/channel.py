"""
Pydantic schemas for channels and channel groups.
"""
from typing import List, Optional
from pydantic import BaseModel


class ChannelSchema(BaseModel):
    channel_id: str
    name: str
    language: str
    topic_category: str = "space"
    custom_topics: List[str] = []
    schedule_hour: int = 9
    active: bool = True
    shorts_mode: bool = False
    transition: str = "fade"   # fade | zoom | slide | none | kenburns | parallax
    edit_options: Optional[dict] = None
    voice_clone_id: Optional[str] = None
    instagram: Optional[bool] = None
    instagram_username: Optional[str] = None
    instagram_user_id: Optional[str] = None


class ToggleSchema(BaseModel):
    active: bool


class SocialSchema(BaseModel):
    instagram: Optional[bool] = None
    instagram_username: Optional[str] = None
    tiktok: Optional[bool] = None


class GroupSchema(BaseModel):
    name: str
    channel_ids: List[str]
    topic_category: str = "reddit_stories"
    reddit_avatar_path: Optional[str] = None
    reddit_username: Optional[str] = None
