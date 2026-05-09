"""
Download router - handles video download endpoints
"""
import asyncio
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException

from ..models.schemas import DownloadRequest, TaskResponse
from ..services.task_manager import task_manager
from ..services.download_service import DownloadService

router = APIRouter(prefix="/api/download", tags=["download"])


@router.post("/start", response_model=TaskResponse)
async def start_download(request: DownloadRequest, background_tasks: BackgroundTasks):
    """Start a new download task"""
    # Create task
    task_id = await task_manager.create_task(f"download:{request.url}")

    # Start download in background
    background_tasks.add_task(
        DownloadService.run_download,
        task_id,
        request.url,
        request.time_range,
        request.config_file
    )

    task = await task_manager.get_task(task_id)
    return TaskResponse(**task.to_dict())


@router.get("/status/{task_id}", response_model=TaskResponse)
async def get_download_status(task_id: UUID):
    """Get download task status"""
    task = await task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(**task.to_dict())


@router.post("/cancel/{task_id}")
async def cancel_download(task_id: UUID):
    """Cancel a running download"""
    await task_manager.cancel_task(task_id)
    return {"message": "Download cancelled"}
