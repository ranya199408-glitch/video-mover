"""
Log watcher service - streams log updates via WebSocket
"""
import asyncio
import logging
from pathlib import Path
from typing import Set

from fastapi import WebSocket

from ..config import LOG_FILE

logger = logging.getLogger(__name__)


class LogWatcher:
    """Watches log files and streams new lines via WebSocket"""

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.position = 0
        self._running = False
        self._clients: Set[WebSocket] = set()

    async def start(self):
        """Start watching for new log lines"""
        self._running = True

        if LOG_FILE.exists():
            self.position = LOG_FILE.stat().st_size

        while self._running:
            try:
                if LOG_FILE.exists():
                    current_size = LOG_FILE.stat().st_size

                    if current_size > self.position:
                        with open(LOG_FILE, 'r', encoding='utf-8') as f:
                            f.seek(self.position)
                            new_lines = f.readlines()
                            self.position = f.tell()

                            for line in new_lines:
                                line = line.strip()
                                if line:
                                    for client in self._clients:
                                        try:
                                            await client.send_text(line)
                                        except Exception:
                                            self._clients.discard(client)

                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"Log watcher error: {e}")
                break

    def stop(self):
        """Stop watching"""
        self._running = False

    async def add_client(self, websocket: WebSocket):
        """Add a new WebSocket client"""
        self._clients.add(websocket)

    async def remove_client(self, websocket: WebSocket):
        """Remove a WebSocket client"""
        self._clients.discard(websocket)


# Global log watcher instance
log_watcher: LogWatcher = None


async def get_log_watcher() -> LogWatcher:
    global log_watcher
    if log_watcher is None:
        log_watcher = LogWatcher(None)
    return log_watcher
