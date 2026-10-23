"""
Settings router.
"""
from fastapi import APIRouter
from settings_manager import SettingsManager
from models.settings import SettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["Settings"])
settings_mgr = SettingsManager()


@router.get("")
def get_settings():
    return settings_mgr.get_masked()


@router.put("")
def update_settings(payload: SettingsUpdate):
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    return settings_mgr.update(updates)
