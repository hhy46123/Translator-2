from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .config import Settings, load_settings
from .db import connect_sqlite
from .notebook import add_item, get_item, increment_correct, list_items, mark_learned, wrong_delta
from .schemas import (
    NotebookAddRequest,
    NotebookMarkRequest,
    NotebookWrongDeltaRequest,
)

router = APIRouter()


def get_settings() -> Settings:
    return load_settings()


@router.post("/api/notebook/add")
def add_notebook(payload: NotebookAddRequest, settings: Settings = Depends(get_settings)):
    if not payload.translated_text.strip() or not payload.senses:
        raise HTTPException(status_code=400, detail="Translation required")
    conn = connect_sqlite(settings.notebook_db_path)
    item_id = add_item(
        conn,
        payload.source_text,
        payload.translated_text,
        payload.direction,
        [sense.model_dump() for sense in payload.senses],
    )
    conn.close()
    return {"id": item_id}


@router.post("/api/notebook/{item_id}/mark")
def mark_item(
    item_id: int,
    payload: NotebookMarkRequest,
    settings: Settings = Depends(get_settings),
):
    conn = connect_sqlite(settings.notebook_db_path)
    if not get_item(conn, item_id):
        conn.close()
        raise HTTPException(status_code=404, detail="Not found")
    mark_learned(conn, item_id, payload.learned)
    conn.close()
    return {"status": "ok"}


@router.post("/api/notebook/{item_id}/wrong_delta")
def wrong_delta_item(
    item_id: int,
    payload: NotebookWrongDeltaRequest,
    settings: Settings = Depends(get_settings),
):
    conn = connect_sqlite(settings.notebook_db_path)
    if not get_item(conn, item_id):
        conn.close()
        raise HTTPException(status_code=404, detail="Not found")
    wrong_delta(conn, item_id, payload.delta)
    conn.close()
    return {"status": "ok"}


@router.post("/api/notebook/{item_id}/mark_correct")
def mark_correct_item(item_id: int, settings: Settings = Depends(get_settings)):
    conn = connect_sqlite(settings.notebook_db_path)
    if not get_item(conn, item_id):
        conn.close()
        raise HTTPException(status_code=404, detail="Not found")
    increment_correct(conn, item_id)
    conn.close()
    return {"status": "ok"}


@router.get("/api/notebook/{item_id}/details")
def details(item_id: int, settings: Settings = Depends(get_settings)):
    conn = connect_sqlite(settings.notebook_db_path)
    item = get_item(conn, item_id)
    conn.close()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    return {
        "id": item.id,
        "source_text": item.source_text,
        "translated_text": item.translated_text,
        "direction": item.direction,
        "senses": item.senses,
        "wrong_attempts": item.wrong_attempts,
        "correct_count": item.correct_count,
        "learned": item.learned,
    }


@router.get("/api/notebook")
def list_notebook(settings: Settings = Depends(get_settings)):
    conn = connect_sqlite(settings.notebook_db_path)
    items = list_items(conn, limit=200)
    conn.close()
    return {"items": [item.__dict__ for item in items]}
