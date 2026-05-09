"""
Download service - wraps f2 CLI for downloading TikTok videos
"""
import asyncio
import logging
import re
from pathlib import Path
from typing import Optional
from uuid import UUID

from ..services.task_manager import task_manager, TaskStatus
from ..config import PROJECT_ROOT, CONFIG_FILE

logger = logging.getLogger(__name__)


class DownloadService:

    @staticmethod
    async def run_download(task_id: UUID, url: str, time_range: Optional[str] = None, config_file: Optional[str] = None):
        """Run f2 tk download and stream output as task progress"""
        config_path = config_file or str(CONFIG_FILE)

        cmd = ['f2', 'tk', '-c', config_path, '-u', url]
        if time_range:
            cmd.extend(['-i', time_range])

        logger.info(f"Starting download: {' '.join(cmd)}")

        try:
            await task_manager.set_status(task_id, TaskStatus.RUNNING)

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.PIPE,
                stderr=asyncio.STDOUT,
                cwd=str(PROJECT_ROOT)
            )

            output_files = []

            async for line in process.stdout:
                decoded = line.decode('utf-8', errors='replace').strip()
                logger.debug(f"f2 output: {decoded}")

                # Parse progress
                progress = None
                if "%" in decoded:
                    match = re.search(r'(\d+)%', decoded)
                    if match:
                        progress = int(match.group(1))

                # Check for downloaded file path
                if '.mp4' in decoded.lower() or 'Downloaded' in decoded or '下载' in decoded:
                    output_files.append(decoded)

                await task_manager.update_progress(task_id, progress=progress, log=decoded)

                # Check for cancellation
                if await task_manager.is_cancelled(task_id):
                    process.terminate()
                    await task_manager.set_status(task_id, TaskStatus.CANCELLED)
                    return

            return_code = await process.wait()

            if return_code == 0:
                await task_manager.set_status(task_id, TaskStatus.COMPLETED, result={"files": output_files})
                logger.info(f"Download completed: {output_files}")
            else:
                error = f"Download failed with exit code {return_code}"
                await task_manager.set_status(task_id, TaskStatus.FAILED, error=error)
                logger.error(error)

        except Exception as e:
            error = f"Download error: {str(e)}"
            await task_manager.set_status(task_id, TaskStatus.FAILED, error=error)
            logger.exception(error)
