from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.schemas.assistant import LearnPhraseRequest, DictionaryResponse, DictionaryEntry, FeedbackRequest
from app.services.intent_dictionary import (
    add_dictionary_entry,
    list_dictionary_entries,
    load_custom_entries,
    phrase_from_question,
    remove_dictionary_entry,
)
from app.services.style_preferences import record_feedback

router = APIRouter()


@router.get("/dictionary", response_model=DictionaryResponse)
def get_dictionary():
    entries = list_dictionary_entries()
    return DictionaryResponse(entries=[DictionaryEntry(**e) for e in entries])


@router.post("/learn-phrase")
def learn_phrase(payload: LearnPhraseRequest):
    add_dictionary_entry(payload.phrase, payload.intent, payload.response_style)
    return {"status": "ok"}


@router.delete("/dictionary")
def delete_dictionary_entry(phrase: str = Query(...)):
    """Remove a custom-learned phrase from the dictionary."""
    remove_dictionary_entry(phrase)
    return {"status": "ok", "removed": phrase}


@router.get("/dictionary/custom", response_model=DictionaryResponse)
def get_custom_dictionary():
    """Return only the user-added (custom) entries, not the built-in defaults."""
    entries = load_custom_entries()
    return DictionaryResponse(entries=[DictionaryEntry(**e) for e in entries])


@router.post("/feedback")
def feedback(payload: FeedbackRequest):
    phrase = phrase_from_question(payload.question)
    if payload.response_style == "auto":
        return {"status": "ignored", "reason": "auto-style has no fixed mapping"}

    record_feedback(payload.question, payload.response_style, payload.useful)

    if payload.useful:
        add_dictionary_entry(phrase, "general", payload.response_style)
        return {"status": "learned", "phrase": phrase}

    remove_dictionary_entry(phrase)
    return {"status": "removed", "phrase": phrase}
