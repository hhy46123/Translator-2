from __future__ import annotations

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import Settings, load_settings
from .db import connect_sqlite
from .notebook import list_items
from .routes_notebook import router as notebook_router
from .routes_translate import router as translate_router
from .startup import ensure_notebook, ensure_offline_dict

app = FastAPI(title="Offline EN↔KO Translator")

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
def on_startup() -> None:
    settings = load_settings()
    ensure_offline_dict(settings)
    ensure_notebook(settings)


@app.get("/", response_class=HTMLResponse)
def translate_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("translate.html", {"request": request})


@app.get("/notebook", response_class=HTMLResponse)
def notebook_page(request: Request, settings: Settings = Depends(load_settings)) -> HTMLResponse:
    conn = connect_sqlite(settings.notebook_db_path)
    items = list_items(conn, limit=200)
    conn.close()
    return templates.TemplateResponse(
        "notebook.html",
        {"request": request, "items": [item.__dict__ for item in items]},
    )


app.include_router(translate_router)
app.include_router(notebook_router)
