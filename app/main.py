import webbrowser

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routes.api import router as api_router
from app.routes.pages import router as pages_router
from app.routes.websocket import router as ws_router
from app.services.cleanup_service import CleanupService
from app.services.meeting_service import meeting_service
from app.utils.network import get_lan_ip

app = FastAPI(title="LAN AI Meeting Room")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(pages_router)
app.include_router(api_router)
app.include_router(ws_router)


@app.on_event("startup")
async def startup_event() -> None:
    CleanupService.clean_temp_dir()
    meeting_service.create_meeting()
    host_url = f"http://127.0.0.1:{settings.port}/"
    try:
        webbrowser.open(host_url)
    except Exception:
        pass
    print(f"Host Console: {host_url}")
    print(f"LAN Join URL: http://{get_lan_ip()}:{settings.port}/join")


if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False)
