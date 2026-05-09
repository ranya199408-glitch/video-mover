"""
Web application configuration
"""
import os
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
CONFIG_FILE = PROJECT_ROOT / "my_apps.yaml"
DOWNLOAD_DIR = PROJECT_ROOT / "Download"
DEDUP_DIR = PROJECT_ROOT / "Dedup"
UPLOAD_DIR = PROJECT_ROOT / "Upload"
LOG_FILE = PROJECT_ROOT / "app.log"

# Web server settings
HOST = "0.0.0.0"
PORT = 8000

# Allowed origins for CORS
ALLOWED_ORIGINS = ["*"]

# Static files path
STATIC_DIR = Path(__file__).parent / "static"
