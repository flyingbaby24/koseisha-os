"""Serve the production bundle with the existing API process."""
from pathlib import Path
import re

from fastapi import FastAPI
from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles

DIST = Path(__file__).resolve().parents[2] / "threejs" / "dist"


class FrontendFiles(StaticFiles):
    async def get_response(self, path, scope):
        path = path.replace("\\", "/")
        # Source maps and hidden files are not public frontend assets.
        if path.endswith(".map") or any(part.startswith(".") and part != "." for part in Path(path).parts):
            raise HTTPException(status_code=404)
        response = await super().get_response(path, scope)
        if path.startswith("assets/") and re.search(r"-[A-Za-z0-9_-]+\.(js|css)$", path):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            response.headers["Cache-Control"] = "no-cache"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response


def mount_frontend(app: FastAPI, directory: Path = DIST, *, required: bool = False):
    if not (directory / "index.html").is_file():
        if required:
            raise RuntimeError(f"Production frontend missing: {directory / 'index.html'}")
        return
    # Called after all API routes. No SPA catch-all: this UI has no path router,
    # and an unknown API/asset URL must remain a 404 rather than receive HTML.
    app.mount("/", FrontendFiles(directory=directory, html=True), name="frontend")
