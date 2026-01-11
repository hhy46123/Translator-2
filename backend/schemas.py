from __future__ import annotations

from pydantic import BaseModel


class TranslateRequest(BaseModel):
    text: str
    direction: str = "auto"


class SenseItem(BaseModel):
    sense_id: int
    entry_id: int
    ko_headword: str
    definition_ko: str | None
    en_equivalents: list[str]


class TranslateResponse(BaseModel):
    source_text: str
    direction: str
    provider_used: str
    translation_success: bool
    translated: str
    senses: list[SenseItem]


class NotebookAddRequest(BaseModel):
    source_text: str
    translated_text: str
    direction: str
    senses: list[SenseItem]


class NotebookMarkRequest(BaseModel):
    learned: bool


class NotebookWrongDeltaRequest(BaseModel):
    delta: int
