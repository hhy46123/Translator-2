from __future__ import annotations

from fastapi import APIRouter, Depends

from .config import Settings, load_settings
from .db import connect_sqlite
from .dict_query import search_dictionary
from .schemas import TranslateRequest, TranslateResponse

router = APIRouter()


def get_settings() -> Settings:
    return load_settings()


def _format_translation(senses) -> str:
    parts = []
    for idx, sense in enumerate(senses, start=1):
        equivalents = ", ".join(sense.en_equivalents) if sense.en_equivalents else ""
        definition = sense.definition_ko or ""
        detail = "; ".join([p for p in [equivalents, definition] if p])
        parts.append(f"{idx}) {detail}".strip())
    return "\n".join(parts)


@router.post("/api/translate", response_model=TranslateResponse)
def translate(payload: TranslateRequest, settings: Settings = Depends(get_settings)):
    text = payload.text.strip()
    if not text:
        return TranslateResponse(
            source_text=payload.text,
            direction=payload.direction,
            provider_used="offline_dict",
            translation_success=False,
            translated="",
            senses=[],
        )

    conn = connect_sqlite(settings.offline_dict_db_path)
    senses = search_dictionary(conn, text, payload.direction, settings.max_senses)
    conn.close()

    translated = _format_translation(senses) if senses else ""
    return TranslateResponse(
        source_text=text,
        direction=payload.direction,
        provider_used="offline_dict",
        translation_success=bool(translated),
        translated=translated,
        senses=senses,
    )
