"""
Dedup router - handles video deduplication endpoints
"""
from uuid import UUID
import os

from fastapi import APIRouter, BackgroundTasks, HTTPException

from ..models.schemas import DedupRequest, TaskResponse, VIDEO_CONFIG_GROUPS
from ..services.task_manager import task_manager
from ..services.dedup_service import DedupService

router = APIRouter(prefix="/api/dedup", tags=["dedup"])


@router.post("/process", response_model=TaskResponse)
async def process_dedup(request: DedupRequest, background_tasks: BackgroundTasks):
    """Start a video deduplication task"""
    # Validate input file exists
    if not os.path.exists(request.input_file):
        raise HTTPException(status_code=400, detail=f"Input file not found: {request.input_file}")

    # Create task
    task_id = await task_manager.create_task(f"dedup:{os.path.basename(request.input_file)}")

    # Start dedup in background
    background_tasks.add_task(
        DedupService.run_dedup,
        task_id,
        request.input_file,
        request.output_file,
        request.config
    )

    task = await task_manager.get_task(task_id)
    return TaskResponse(**task.to_dict())


@router.get("/status/{task_id}", response_model=TaskResponse)
async def get_dedup_status(task_id: UUID):
    """Get dedup task status"""
    task = await task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(**task.to_dict())


@router.get("/config/groups")
async def get_config_groups():
    """Get VideoConfig options grouped by category"""
    return VIDEO_CONFIG_GROUPS


@router.post("/cancel/{task_id}")
async def cancel_dedup(task_id: UUID):
    """Cancel a running dedup task"""
    await task_manager.cancel_task(task_id)
    return {"message": "Dedup cancelled"}
