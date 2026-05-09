"""
FastAPI main application for video-mover web UI
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from .config import HOST, PORT, ALLOWED_ORIGINS, STATIC_DIR
from .routers import download, dedup, config, logs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("Video-Mover Web starting up...")
    yield
    logger.info("Video-Mover Web shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Video-Mover Web",
    description="Web interface for video downloading, deduplication, and upload",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(download.router)
app.include_router(dedup.router)
app.include_router(config.router)
app.include_router(logs.router)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main web UI"""
    html_file = STATIC_DIR / "index.html"
    with open(html_file, 'r', encoding='utf-8') as f:
        return f.read()


# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
