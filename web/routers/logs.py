"""
Logs router - handles WebSocket log streaming
"""
import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..config import LOG_FILE
from ..services.log_watcher import log_watcher

logger = logging.getLogger(__name__)

router = APIRouter(tags=["logs"])


@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket endpoint for streaming logs"""
    await websocket.accept()
    logger.info("WebSocket client connected")

    client_log_file = LOG_FILE
    position = 0

    try:
        # Send existing logs first
        if client_log_file.exists():
            with open(client_log_file, 'r', encoding='utf-8') as f:
                # Send last 100 lines
                lines = f.readlines()
                for line in lines[-100:]:
                    await websocket.send_text(line.strip())

        # Stream new logs
        if client_log_file.exists():
            position = client_log_file.stat().st_size

        while True:
            if client_log_file.exists():
                current_size = client_log_file.stat().st_size

                if current_size > position:
                    with open(client_log_file, 'r', encoding='utf-8') as f:
                        f.seek(position)
                        new_lines = f.readlines()
                        position = f.tell()

                        for line in new_lines:
                            line = line.strip()
                            if line:
                                await websocket.send_text(line)

            await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
