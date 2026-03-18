from app.services.query import _rerank_scored_candidates, _score_with_metadata


def test_reranker_diversifies_same_document_results():
    candidates = [
        {"score": 0.92, "document_id": 1, "tema": "Riesgos"},
        {"score": 0.90, "document_id": 1, "tema": "Riesgos"},
        {"score": 0.89, "document_id": 1, "tema": "Riesgos"},
        {"score": 0.84, "document_id": 2, "tema": "Criptografía"},
        {"score": 0.82, "document_id": 3, "tema": "Ingeniería social"},
    ]

    out = _rerank_scored_candidates(candidates, top_k=3)

    doc_ids = [x["document_id"] for x in out]
    assert len(out) == 3
    assert len(set(doc_ids)) >= 2


def test_score_with_metadata_boosts_definitions_when_question_asks_definition():
    question = "¿Qué es el riesgo residual? Dame una definición"

    base = 0.40
    text_generic = "El riesgo residual permanece después de aplicar controles."
    text_definition = "Definición: riesgo residual es el riesgo remanente tras mitigaciones."

    score_generic = _score_with_metadata(question, text_generic, base, {"tipo_contenido": "teoria"})
    score_definition = _score_with_metadata(question, text_definition, base, {"tipo_contenido": "definicion"})

    assert score_definition > score_generic
