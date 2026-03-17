from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.schemas.assistant import (
    LearnPhraseRequest,
    DictionaryResponse,
    DictionaryEntry,
    FeedbackRequest,
    FineTuneStatusResponse,
    FineTuneExportResponse,
)
from app.services.intent_dictionary import (
    add_dictionary_entry,
    list_dictionary_entries,
    load_custom_entries,
    phrase_from_question,
    remove_dictionary_entry,
)
from app.services.style_preferences import record_feedback
from app.services.fine_tuning import record_approved_example, get_fine_tune_status, export_lora_dataset

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
    if payload.useful and payload.answer_text:
        record_approved_example(
            question=payload.question,
            answer=payload.answer_text,
            style=payload.response_style,
            branch=payload.branch,
        )

    if payload.useful:
        add_dictionary_entry(phrase, "general", payload.response_style)
        return {"status": "learned", "phrase": phrase}

    remove_dictionary_entry(phrase)
    return {"status": "removed", "phrase": phrase}


@router.get("/fine-tune/status", response_model=FineTuneStatusResponse)
def fine_tune_status():
    return FineTuneStatusResponse(**get_fine_tune_status())


@router.post("/fine-tune/export", response_model=FineTuneExportResponse)
def fine_tune_export(include_chats: bool = True):
    return FineTuneExportResponse(**export_lora_dataset(include_chats=include_chats))
