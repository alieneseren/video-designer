from .settings import router as settings_router
from .channels import router as channels_router
from .media import router as media_router
from .browser import router as browser_router
from .outputs import router as outputs_router
from .video_patch import router as video_patch_router
from .procedural_video import router as procedural_video_router

__all__ = [
    "settings_router",
    "channels_router",
    "media_router",
    "browser_router",
    "outputs_router",
    "video_patch_router",
    "procedural_video_router",
]


