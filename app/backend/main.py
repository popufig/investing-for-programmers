from contextlib import asynccontextmanager
import os
from pathlib import Path

from dotenv import dotenv_values
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import init_db
from .routers import analytics, macro, portfolio, stocks, thesis, watchlist

_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
_env = dotenv_values(_ENV_PATH)

APP_HOST = _env.get("APP_HOST", "0.0.0.0")
APP_PORT = int(_env.get("APP_PORT", "18600"))

FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Investment Analysis System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(stocks.router, prefix="/api/stocks", tags=["stocks"])
app.include_router(watchlist.router, prefix="/api/watchlist", tags=["watchlist"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(macro.router, prefix="/api/macro", tags=["macro"])
app.include_router(thesis.router, prefix="/api/thesis", tags=["thesis"])


# Serve React build if it exists
if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/")
    def serve_index():
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        # Let API routes pass through; serve index.html for everything else
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
else:
    @app.get("/")
    def root():
        return {"status": "ok", "message": "Run 'npm run build' in frontend/ to serve the UI"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=APP_HOST,
        port=APP_PORT,
        reload=True,
    )
