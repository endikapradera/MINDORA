from fastapi import APIRouter, HTTPException
import uuid
import re
from typing import Optional

from app.schemas.ask import AskRequest, AskResponse
from app.services.chat_memory import append_chat_turn, get_chat_history
from app.services.query import retrieve_chunks
from app.services.llm import generate_answer
from app.storage.database import get_session
from app.storage.models import Document
from sqlmodel import select

router = APIRouter()


_LOW_EVIDENCE_AVG_SCORE = 0.22
_LOW_EVIDENCE_TOP_SCORE = 0.30


def _question_is_unclear(question: str) -> bool:
    q = (question or "").strip()
    if len(q) < 4:
        return True
    if re.fullmatch(r"[\W_]+", q):
        return True
    words = re.findall(r"[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9]+", q)
    return len(words) < 2


def _unclear_question_message() -> str:
    return (
        "No he entendido bien tu pregunta. Prueba con una pregunta más concreta.\n\n"
        "Sugerencias de ejemplo:\n"
        "- 'Explícame la fotosíntesis en 5 pasos'\n"
        "- 'Hazme un resumen corto del tema de mitosis'\n"
        "- 'Ponme 10 preguntas tipo test de la unidad 2'\n"
        "- '¿Qué diferencias hay entre mitosis y meiosis?'"
    )


def _smalltalk_answer(question: str) -> Optional[str]:
    q = (question or "").strip().lower()
    q_norm = re.sub(r"\s+", " ", q)
    greetings = [
        "hola",
        "hola como estas",
        "hola cómo estás",
        "hola que tal",
        "hola qué tal",
        "como estas",
        "cómo estás",
        "que tal",
        "qué tal",
        "buenas",
        "buenos dias",
        "buenos días",
        "buenas tardes",
        "buenas noches",
    ]
    if q_norm in greetings:
        return (
            "¡Hola! Estoy listo para ayudarte 😊\n\n"
            "Si quieres estudiar, prueba con algo como:\n"
            "- 'Resúmeme este tema en 5 puntos'\n"
            "- 'Explícame la diferencia entre X e Y'\n"
            "- 'Ponme 10 preguntas tipo test de este documento'"
        )
    return None


def _looks_like_code_request(question: str) -> bool:
    q = question or ""
    lower = q.lower()

    if "```" in q:
        return True

    code_markers = [
        "function ", "def ", "class ", "const ", "let ", "var ", "return ",
        "import ", "from ", "console.log", "try:", "except", "=>", "{}", "();",
        "javascript", "typescript", "python", "java", "c++", "sql", "html", "css",
        "bug", "error", "traceback", "api", "endpoint", "refactor", "regex",
    ]
    if any(marker in lower for marker in code_markers):
        return True

    lines = q.splitlines()
    suspicious_lines = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if re.search(r'[{}();=<>"\']', stripped) and len(stripped) >= 8:
            suspicious_lines += 1
    return suspicious_lines >= 2


def _dimseg_knowledge_answer(question: str) -> Optional[str]:
    q = (question or "").lower()

    if "1-resumen dimseg" in q or "1 resumen dimseg" in q or ("pdf" in q and "dimseg" in q):
        return (
            "1) El temario trata sobre seguridad de la información, gestión del riesgo y amenazas informáticas.\n"
            "2) Explica conceptos como riesgo, riesgo residual, aceptación, mitigación, transferencia y evitación.\n"
            "3) Incluye ataques frecuentes: phishing, vishing, spoofing, Man in the Middle, DoS/DDoS, fuerza bruta y SQL Injection.\n"
            "4) Destaca la ingeniería social y el factor humano como puntos críticos en la seguridad.\n"
            "5) La idea clave es que la seguridad no depende solo de la tecnología, sino también de procesos, controles y concienciación del usuario."
        )
    if "seguridad de la información" in q:
        return "La seguridad de la información es el conjunto de medidas destinadas a proteger la confidencialidad, integridad y disponibilidad de los datos y sistemas."
    if "riesgo residual" in q:
        return "El riesgo residual es el riesgo que sigue existiendo después de aplicar controles o medidas de seguridad. Nunca suele desaparecer del todo, solo reducirse a niveles aceptables."
    if "riesgo aceptable" in q and "inasumible" in q:
        return "Un riesgo aceptable es aquel que una organización puede asumir tras evaluarlo; un riesgo inasumible es tan alto que exige medidas inmediatas o incluso evitar la actividad."
    if "gestión del riesgo" in q or "estrategias" in q and "riesgo" in q:
        return "Las estrategias principales de gestión del riesgo son: evitarlo, mitigarlo, transferirlo y aceptarlo. La organización elige según impacto, probabilidad y coste de los controles."
    if "ingeniería social" in q:
        return "La ingeniería social es una técnica de ataque que manipula a las personas para obtener información o acceso. Suele pasar por reconocimiento, engaño, ganarse la confianza y explotación final."
    if "phishing" in q:
        return "El phishing es un ataque de ingeniería social en el que el atacante suplanta una entidad legítima, normalmente por correo o web falsa, para robar credenciales o datos."
    if "vishing" in q:
        return "El vishing es una variante del phishing realizada por llamada telefónica o mensajes de voz para engañar a la víctima y obtener información sensible."
    if "shoulder surfing" in q:
        return "El shoulder surfing consiste en observar físicamente a una persona mientras introduce contraseñas, PIN o datos confidenciales."
    if "dumpster diving" in q:
        return "El dumpster diving consiste en buscar información útil en papeles, dispositivos o residuos desechados por una organización o usuario."
    if "fuerza bruta" in q:
        return "Un ataque de fuerza bruta intenta descubrir una contraseña probando de manera masiva muchas combinaciones posibles hasta acertar."
    if "diccionario" in q and "ataque" in q:
        return "Un ataque por diccionario prueba contraseñas usando listas de palabras comunes, nombres y combinaciones frecuentes, por lo que es más rápido que la fuerza bruta pura."
    if "dos" in q and "ddos" in q:
        return "La diferencia es que un DoS suele originarse desde una sola fuente, mientras que un DDoS utiliza múltiples equipos comprometidos para saturar el servicio de forma distribuida."
    if re.search(r"\bdos\b", q):
        return "Un ataque DoS busca dejar un servicio inaccesible saturándolo con peticiones o explotando recursos hasta impedir su disponibilidad."
    if "man in the middle" in q:
        return "Un ataque Man in the Middle ocurre cuando un atacante se sitúa entre dos partes que se comunican para interceptar, leer o incluso modificar la información transmitida."
    if "dns poisoning" in q:
        return "El DNS poisoning manipula respuestas DNS para redirigir a la víctima a una dirección falsa aunque crea estar entrando en un sitio legítimo."
    if "spoofing" in q:
        return "El spoofing consiste en suplantar una identidad digital, como una IP, un correo, una web o un remitente, para engañar al receptor."
    if "sql injection" in q:
        return "Una SQL Injection es un ataque a aplicaciones web en el que se introducen comandos SQL maliciosos en formularios o parámetros para acceder, modificar o borrar datos."
    if "zero-day" in q or "zero day" in q:
        return "Un ataque Zero-Day explota una vulnerabilidad que aún no ha sido corregida o que ni siquiera era conocida por el fabricante."
    if "clickjacking" in q:
        return "El clickjacking engaña al usuario para que pulse sobre elementos invisibles o superpuestos creyendo que hace otra acción distinta."
    if "codificar" in q and "cifrar" in q:
        return "Codificar transforma la información para cambiar su formato o representarla de otro modo; cifrar la protege criptográficamente para que solo quien tenga la clave pueda leerla."
    if "factor humano" in q or "eslabón más débil" in q:
        return "El factor humano suele considerarse el eslabón más débil porque muchos ataques explotan errores, descuidos o falta de formación del usuario en lugar de vulnerabilidades técnicas."
    if "controles de seguridad" in q or "qué controles" in q:
        return "Algunos controles de seguridad que reducen el riesgo son: autenticación multifactor, formación al usuario, cifrado, copias de seguridad, segmentación de red, actualizaciones y monitorización."
    return None


def _fallback_queries(question: str) -> list[str]:
    q = (question or "").strip()
    variants: list[str] = []

    # Remove common pedagogical prefixes
    cleaned = re.sub(
        r"(?i)^(expl[ií]camelo\s+f[aá]cil|expl[ií]camelo\s+paso\s+a\s+paso|expl[ií]camelo\s+en\s+1\s+minuto|"
        r"expl[ií]camelo\s+como\s+si\s+fuera\s+examen|res[uú]meme|resumen\s+corto|resumen\s+largo)\s*:\s*",
        "",
        q,
    ).strip()
    if cleaned and cleaned != q:
        variants.append(cleaned)

    # Remove explicit references to file extension and punctuation noise
    no_ext = re.sub(r"(?i)\.pdf\b", "", cleaned or q)
    no_ext = re.sub(r"[\(\)\[\]{};,_]+", " ", no_ext)
    no_ext = re.sub(r"\s+", " ", no_ext).strip()
    if no_ext and no_ext not in variants and no_ext != q:
        variants.append(no_ext)

    # Keep only meaningful tokens as a last semantic fallback
    tokens = re.findall(r"[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\-]{3,}", no_ext)
    if tokens:
        compact = " ".join(tokens[:14]).strip()
        if compact and compact not in variants and compact != q:
            variants.append(compact)

    return variants[:3]


def _infer_document_id_from_question(branch: str, question: str) -> Optional[int]:
    q_tokens = set(re.findall(r"[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9]{3,}", (question or "").lower()))
    if not q_tokens:
        return None
    try:
        with get_session(branch) as session:
            docs = session.exec(select(Document)).all()
    except Exception:
        return None

    best_id = None
    best_score = 0
    for doc in docs:
        filename = (doc.filename or "").lower().replace(".pdf", "")
        f_tokens = set(re.findall(r"[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9]{3,}", filename))
        score = len(q_tokens.intersection(f_tokens))
        if score > best_score:
            best_score = score
            best_id = doc.id
    return best_id if best_score >= 1 else None


@router.post("", response_model=AskResponse)
def ask(payload: AskRequest, branch: str):
    session_id = payload.session_id or uuid.uuid4().hex
    document_id = payload.document_id or _infer_document_id_from_question(branch, payload.question)

    smalltalk = _smalltalk_answer(payload.question)
    if smalltalk:
        append_chat_turn(branch, session_id, payload.question, smalltalk)
        return AskResponse(answer=smalltalk, contexts=[], sources=[], session_id=session_id)

    effective_mode = payload.response_style
    if effective_mode == "auto" and _looks_like_code_request(payload.question):
        effective_mode = "codigo"

    if effective_mode == "codigo":
        try:
            history = get_chat_history(branch, session_id)
            answer = generate_answer(payload.question, [], "codigo", history=history)
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=f"No se pudo generar respuesta de código: {str(exc)}")
        append_chat_turn(branch, session_id, payload.question, answer)
        return AskResponse(answer=answer, contexts=[], sources=[], session_id=session_id)

    if _question_is_unclear(payload.question):
        return AskResponse(
            answer=_unclear_question_message(),
            contexts=[],
            sources=[],
            session_id=session_id,
        )

    curated_answer = _dimseg_knowledge_answer(payload.question)
    if curated_answer:
        curated_sources: list[str] = []
        if document_id is not None:
            try:
                with get_session(branch) as session:
                    doc = session.get(Document, document_id)
                if doc:
                    curated_sources = [f"{doc.filename} (respuesta guiada MINDORA)"]
            except Exception:
                curated_sources = []
        return AskResponse(
            answer=curated_answer,
            contexts=[],
            sources=curated_sources,
            session_id=session_id,
        )

    # Fast path: if branch has no documents, avoid expensive embedding/search cycle
    try:
        with get_session(branch) as session:
            has_docs = session.exec(select(Document.id).limit(1)).first() is not None
        if not has_docs:
            return AskResponse(
                answer=(
                    "Esta rama todavía no tiene documentos.\n\n"
                    "Sugerencia: ve a Temarios → Ingesta de documentos y sube primero el PDF '1-RESUMEN DIMSEG.pdf'."
                ),
                contexts=[],
                sources=[],
                session_id=session_id,
            )
    except Exception:
        pass

    results = retrieve_chunks(branch, payload.question, payload.top_k, document_id=document_id)

    # Fallback retrieval for noisy/over-specified questions (e.g., with file names)
    if not results:
        for alt_query in _fallback_queries(payload.question):
            alt_results = retrieve_chunks(
                branch,
                alt_query,
                min(12, max(payload.top_k + 3, 8)),
                document_id=document_id,
            )
            if alt_results:
                results = alt_results
                break

    contexts = []
    for i, r in enumerate(results, start=1):
        filename = r.get("filename", "documento")
        page = int(r.get("pagina", 0) or 0)
        tema = r.get("tema", "Tema general")
        header = f"[FUENTE {i}] {filename}"
        if page > 0:
            header += f" | p.{page}"
        if tema:
            header += f" | {tema}"
        contexts.append(f"{header}\n{r['text']}")
    sources = []
    for r in results:
        filename = r.get("filename", "documento")
        chunk_index = r.get("chunk_index", 0)
        page = int(r.get("pagina", 0) or 0)
        tema = r.get("tema", "Tema general")
        content_type = r.get("tipo_contenido", "teoria")
        if page > 0:
            sources.append(f"{filename} (p.{page}, chunk {chunk_index}, {content_type}, {tema})")
        else:
            sources.append(f"{filename} (chunk {chunk_index}, {content_type}, {tema})")
    if not contexts:
        return AskResponse(
            answer=(
                "No encontré información suficiente en los documentos de esta rama para responder con precisión.\n\n"
                "Sugerencia: sube apuntes sobre ese tema o reformula la pregunta con términos del temario."
            ),
            contexts=[],
            sources=[],
            session_id=session_id,
        )

    # Safety guard: if retrieval evidence is weak, do not hallucinate.
    if results:
        top_score = float(results[0].get("score", 0.0))
        avg_score = sum(float(r.get("score", 0.0)) for r in results) / max(1, len(results))
        if top_score < _LOW_EVIDENCE_TOP_SCORE and avg_score < _LOW_EVIDENCE_AVG_SCORE:
            return AskResponse(
                answer=(
                    "No lo sé con suficiente certeza usando la evidencia disponible en esta rama.\n\n"
                    "Prueba con una pregunta más concreta o añade material adicional sobre ese tema."
                ),
                contexts=contexts,
                sources=sources,
                session_id=session_id,
            )

    try:
        history = get_chat_history(branch, session_id)
        answer = generate_answer(payload.question, contexts, effective_mode, history=history)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                f"No se pudo generar respuesta en este momento: {str(exc)}. "
                "Inténtalo de nuevo o usa una pregunta más concreta."
            ),
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail=(
                "Se produjo un error inesperado al procesar tu pregunta. "
                "Prueba reformularla así: 'Explícame fácil el PDF <nombre>' o "
                "'resúmeme el documento en 5 puntos'."
            ),
        )
    append_chat_turn(branch, session_id, payload.question, answer)
    return AskResponse(answer=answer, contexts=contexts, sources=sources, session_id=session_id)
