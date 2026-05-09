"""
Config router - handles configuration management
"""
import os
import yaml
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..config import CONFIG_FILE, PROJECT_ROOT, DOWNLOAD_DIR, DEDUP_DIR, UPLOAD_DIR
from ..models.schemas import ConfigUpdateRequest, VideoConfigSchema

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("/yaml")
async def get_config():
    """Get current my_apps.yaml configuration"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            content = yaml.safe_load(f)
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read config: {str(e)}")


@router.put("/yaml")
async def update_config(request: ConfigUpdateRequest):
    """Update my_apps.yaml configuration"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(request.content, f, allow_unicode=True, default_flow_style=False)
        return {"message": "Configuration updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write config: {str(e)}")


@router.get("/paths")
async def get_paths():
    """Get configured paths"""
    return {
        "project_root": str(PROJECT_ROOT),
        "download_dir": str(DOWNLOAD_DIR),
        "dedup_dir": str(DEDUP_DIR),
        "upload_dir": str(UPLOAD_DIR),
        "config_file": str(CONFIG_FILE)
    }


@router.get("/video-defaults", response_model=VideoConfigSchema)
async def get_video_defaults():
    """Get default VideoConfig settings"""
    return VideoConfigSchema()


@router.get("/resolve-path")
async def resolve_path(filename: str):
    """Resolve a filename to absolute path by searching known directories"""
    # Direct check first
    if os.path.isabs(filename) and os.path.exists(filename):
        return {"path": filename, "found": True}

    # Search in known directories
    search_dirs = [
        DOWNLOAD_DIR,
        DEDUP_DIR,
        UPLOAD_DIR,
        PROJECT_ROOT,
        Path.home() / "Downloads",
    ]

    for directory in search_dirs:
        if directory and os.path.exists(directory):
            # Search in directory
            candidate = os.path.join(directory, filename)
            if os.path.exists(candidate):
                return {"path": candidate, "found": True}
            # Recursive search in subdirs (limited depth)
            for root, dirs, files in os.walk(directory):
                if filename in files:
                    return {"path": os.path.join(root, filename), "found": True}
                # Limit depth
                if root.count(os.sep) - str(directory).count(os.sep) > 2:
                    break

    return {"path": filename, "found": False}
