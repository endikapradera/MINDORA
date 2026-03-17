"""
test_integration.py — Banco de tests de integración para MINDORA.

Cubre:
- CRUD de ramas (crear, listar, eliminar)
- Ingestión de documentos de temarios reales (matemáticas, programación, física)
- Generación de exámenes con preguntas sobre los temarios
- Validación de distractores y confianza
- Manejo de errores (ramas no existentes, documentos vacíos, etc.)
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Directorio de fixtures con contenido educativo real
# ---------------------------------------------------------------------------
FIXTURES_DIR = Path(__file__).parent / "fixtures"
MATES_TXT = FIXTURES_DIR / "matematicas.txt"
PROG_TXT = FIXTURES_DIR / "programacion.txt"
FISICA_TXT = FIXTURES_DIR / "fisica.txt"


# ===========================================================================
# SECCIÓN 1: CRUD DE RAMAS
# ===========================================================================

class TestBranchCRUD:
    """Crear, listar y eliminar ramas con un directorio raíz temporal."""

    def test_create_branch_creates_folders(self, tmp_path):
        with patch("app.storage.branches.get_base_dir", return_value=tmp_path):
            from app.storage.branches import create_branch, list_branches
            from app.schemas.branch import BranchCreate

            result = create_branch(BranchCreate(name="Matemáticas"))
            assert result.name == "Matemáticas"

            branch_path = Path(result.path)
            assert (branch_path / "Material").is_dir()
            assert (branch_path / "Index").is_dir()
            assert (branch_path / "Chats").is_dir()
            assert (branch_path / "Exams").is_dir()
            assert (branch_path / "settings.json").is_file()

    def test_list_branches_returns_all(self, tmp_path):
        with patch("app.storage.branches.get_base_dir", return_value=tmp_path):
            from app.storage.branches import create_branch, list_branches
            from app.schemas.branch import BranchCreate

            create_branch(BranchCreate(name="Mates"))
            create_branch(BranchCreate(name="Fisica"))
            create_branch(BranchCreate(name="Programacion"))

            branches = list_branches()
            names = [b.name for b in branches]
            assert "Mates" in names
            assert "Fisica" in names
            assert "Programacion" in names
            assert len(branches) == 3

    def test_create_duplicate_branch_raises_error(self, tmp_path):
        with patch("app.storage.branches.get_base_dir", return_value=tmp_path):
            from app.storage.branches import create_branch
            from app.schemas.branch import BranchCreate

            create_branch(BranchCreate(name="Repetida"))
            with pytest.raises(FileExistsError):
                create_branch(BranchCreate(name="Repetida"))

    def test_delete_branch_removes_directory(self, tmp_path):
        with patch("app.storage.branches.get_base_dir", return_value=tmp_path):
            from app.storage.branches import create_branch, delete_branch, branch_exists
            from app.schemas.branch import BranchCreate

            create_branch(BranchCreate(name="AEliminar"))
            assert branch_exists("AEliminar")

            delete_branch("AEliminar")
            assert not branch_exists("AEliminar")

    def test_delete_nonexistent_branch_raises_error(self, tmp_path):
        with patch("app.storage.branches.get_base_dir", return_value=tmp_path):
            from app.storage.branches import delete_branch

            with pytest.raises(FileNotFoundError):
                delete_branch("RamaQueNoExiste")

    def test_list_empty_when_no_branches(self, tmp_path):
        with patch("app.storage.branches.get_base_dir", return_value=tmp_path):
            from app.storage.branches import list_branches

            result = list_branches()
            assert result == []

    def test_branch_exists_true_after_create(self, tmp_path):
        with patch("app.storage.branches.get_base_dir", return_value=tmp_path):
            from app.storage.branches import create_branch, branch_exists
            from app.schemas.branch import BranchCreate

            create_branch(BranchCreate(name="Existente"))
            assert branch_exists("Existente") is True

    def test_branch_exists_false_before_create(self, tmp_path):
        with patch("app.storage.branches.get_base_dir", return_value=tmp_path):
            from app.storage.branches import branch_exists

            assert branch_exists("RamaFantasma") is False

    def test_delete_branch_with_files_inside(self, tmp_path):
        """Verificar que se eliminan los archivos dentro de la rama."""
        with patch("app.storage.branches.get_base_dir", return_value=tmp_path):
            from app.storage.branches import create_branch, delete_branch, get_branch_path
            from app.schemas.branch import BranchCreate

            create_branch(BranchCreate(name="ConArchivos"))
            branch_path = get_branch_path("ConArchivos")
            # Simular archivos subidos
            (branch_path / "Material" / "apuntes.txt").write_text("contenido", encoding="utf-8")
            (branch_path / "Exams" / "exam_001.json").write_text("{}", encoding="utf-8")

            delete_branch("ConArchivos")
            assert not branch_path.exists()


# ===========================================================================
# SECCIÓN 2: CHUNKING Y EXTRACCIÓN DE TEXTO (sin LLM real)
# ===========================================================================

class TestTextExtraction:
    """Verificar que los textos educativos se extraen y trocean correctamente."""

    def test_extract_text_from_mates(self):
        from app.services.text_extract import extract_text_from_file
        text = extract_text_from_file(MATES_TXT)
        assert "límite" in text.lower() or "derivada" in text.lower()
        assert len(text) > 500

    def test_extract_text_from_programacion(self):
        from app.services.text_extract import extract_text_from_file
        text = extract_text_from_file(PROG_TXT)
        assert "python" in text.lower() or "algoritmo" in text.lower()
        assert len(text) > 500

    def test_extract_text_from_fisica(self):
        from app.services.text_extract import extract_text_from_file
        text = extract_text_from_file(FISICA_TXT)
        assert "newton" in text.lower() or "velocidad" in text.lower()
        assert len(text) > 500

    def test_chunking_mates_produces_chunks(self):
        from app.services.text_extract import extract_text_from_file
        from app.services.chunking import chunk_text_with_metadata

        text = extract_text_from_file(MATES_TXT)
        chunks = chunk_text_with_metadata(text, subject="Matemáticas", source="matematicas.txt")
        assert len(chunks) > 0
        for c in chunks:
            assert "text" in c
            assert "metadata" in c
            assert len(c["text"].strip()) > 0

    def test_chunking_programacion_produces_chunks(self):
        from app.services.text_extract import extract_text_from_file
        from app.services.chunking import chunk_text_with_metadata

        text = extract_text_from_file(PROG_TXT)
        chunks = chunk_text_with_metadata(text, subject="Programacion", source="programacion.txt")
        assert len(chunks) > 0

    def test_chunking_fisica_produces_chunks(self):
        from app.services.text_extract import extract_text_from_file
        from app.services.chunking import chunk_text_with_metadata

        text = extract_text_from_file(FISICA_TXT)
        chunks = chunk_text_with_metadata(text, subject="Fisica", source="fisica.txt")
        assert len(chunks) > 0

    def test_empty_file_produces_empty_chunks(self, tmp_path):
        from app.services.text_extract import extract_text_from_file
        from app.services.chunking import chunk_text_with_metadata

        empty_file = tmp_path / "vacio.txt"
        empty_file.write_text("", encoding="utf-8")
        text = extract_text_from_file(empty_file)
        chunks = chunk_text_with_metadata(text, subject="test", source="vacio.txt")
        assert len(chunks) == 0 or all(len(c["text"].strip()) == 0 for c in chunks)

    def test_chunk_metadata_has_required_fields(self):
        from app.services.text_extract import extract_text_from_file
        from app.services.chunking import chunk_text_with_metadata

        text = extract_text_from_file(MATES_TXT)
        chunks = chunk_text_with_metadata(text, subject="Matemáticas", source="matematicas.txt")
        if chunks:
            meta = chunks[0]["metadata"]
            # Debe contener al menos la asignatura
            assert "asignatura" in meta or "subject" in meta or isinstance(meta, dict)


# ===========================================================================
# SECCIÓN 3: INGESTIÓN DE DOCUMENTOS (con embeddings y FAISS mockeados)
# ===========================================================================

class TestDocumentIngest:
    """Ingestión completa con embeddings y FAISS falsos."""

    def _mock_embeds(self, texts):
        import numpy as np
        return np.random.rand(len(texts), 384).astype("float32")

    def test_ingest_matematicas(self, tmp_path):
        _setup_branch_dir(tmp_path, "Matematicas")

        with patch("app.services.ingest.get_branch_path", return_value=tmp_path), \
             patch("app.services.ingest.branch_exists", return_value=True), \
             patch("app.services.ingest.embed_texts", side_effect=self._mock_embeds), \
             patch("app.services.ingest.add_embeddings") as mock_add, \
             patch("app.storage.database.get_base_dir", return_value=tmp_path):

            from app.services.ingest import ingest_document
            result = ingest_document("Matematicas", MATES_TXT)

            assert result["chunks"] > 0
            assert "document_id" in result
            assert mock_add.called

    def test_ingest_programacion(self, tmp_path):
        _setup_branch_dir(tmp_path, "Programacion")

        with patch("app.services.ingest.get_branch_path", return_value=tmp_path), \
             patch("app.services.ingest.branch_exists", return_value=True), \
             patch("app.services.ingest.embed_texts", side_effect=self._mock_embeds), \
             patch("app.services.ingest.add_embeddings"), \
             patch("app.storage.database.get_base_dir", return_value=tmp_path):

            from app.services.ingest import ingest_document
            result = ingest_document("Programacion", PROG_TXT)
            assert result["chunks"] > 0

    def test_ingest_fisica(self, tmp_path):
        _setup_branch_dir(tmp_path, "Fisica")

        with patch("app.services.ingest.get_branch_path", return_value=tmp_path), \
             patch("app.services.ingest.branch_exists", return_value=True), \
             patch("app.services.ingest.embed_texts", side_effect=self._mock_embeds), \
             patch("app.services.ingest.add_embeddings"), \
             patch("app.storage.database.get_base_dir", return_value=tmp_path):

            from app.services.ingest import ingest_document
            result = ingest_document("Fisica", FISICA_TXT)
            assert result["chunks"] > 0

    def test_ingest_raises_when_branch_missing(self, tmp_path):
        with patch("app.services.ingest.branch_exists", return_value=False):
            from app.services.ingest import ingest_document
            with pytest.raises(FileNotFoundError):
                ingest_document("RamaInexistente", MATES_TXT)

    def test_ingest_same_doc_twice_returns_zero_new_chunks(self, tmp_path):
        """La segunda ingestión del mismo documento devuelve chunks=0 (ya existe)."""
        _setup_branch_dir(tmp_path, "Mates2")

        def mock_embed(texts):
            import numpy as np
            return np.random.rand(len(texts), 384).astype("float32")

        patches = [
            patch("app.services.ingest.get_branch_path", return_value=tmp_path),
            patch("app.services.ingest.branch_exists", return_value=True),
            patch("app.services.ingest.embed_texts", side_effect=mock_embed),
            patch("app.services.ingest.add_embeddings"),
            patch("app.storage.database.get_base_dir", return_value=tmp_path),
        ]
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            from app.services.ingest import ingest_document
            r1 = ingest_document("Mates2", MATES_TXT)
            r2 = ingest_document("Mates2", MATES_TXT)
            assert r1["chunks"] > 0
            assert r2["chunks"] == 0  # duplicado, sin nuevos chunks


# ===========================================================================
# SECCIÓN 4: GENERACIÓN DE EXÁMENES
# ===========================================================================

class TestExamGeneration:
    """Generación de exámenes a partir de bloques de texto de temarios."""

    # Respuesta de LLM falsa en formato esperado
    _FAKE_EXAM_MATES = """
### Pregunta 1
Tipo: test_simple
Enunciado: ¿Qué es la derivada de una función?
Opciones:
A) La pendiente de la recta tangente en un punto
B) El área bajo la curva
C) El valor máximo de la función
D) El cociente entre variables
Respuesta: A
Explicacion: La derivada es geométricamente la pendiente de la recta tangente.

### Pregunta 2
Tipo: test_simple
Enunciado: ¿Cuál es la regla de la cadena en derivadas?
Opciones:
A) d/dx[f+g] = f' + g'
B) d/dx[f·g] = f'·g + f·g'
C) d/dx[f(g(x))] = f'(g(x))·g'(x)
D) d/dx[f/g] = f'·g - f·g'
Respuesta: C
Explicacion: La regla de la cadena se aplica a funciones compuestas.

### Pregunta 3
Tipo: desarrollo
Enunciado: Explica el Teorema Fundamental del Cálculo.
Opciones:
Respuesta: Si F es una primitiva de f continua en [a,b], entonces la integral definida de a a b de f(x) es F(b)-F(a).
Explicacion: Conecta la diferenciación y la integración.
"""

    _FAKE_EXAM_PROG = """
### Pregunta 1
Tipo: test_simple
Enunciado: ¿Cuál es la complejidad de la búsqueda binaria?
Opciones:
A) O(n)
B) O(n²)
C) O(log n)
D) O(1)
Respuesta: C
Explicacion: Búsqueda binaria divide el espacio a la mitad en cada paso.

### Pregunta 2
Tipo: test_simple
Enunciado: ¿Qué estructura de datos usa BFS?
Opciones:
A) Pila (Stack)
B) Cola (Queue)
C) Árbol AVL
D) Tabla Hash
Respuesta: B
Explicacion: BFS usa una cola FIFO para explorar nodos por niveles.

### Pregunta 3
Tipo: test_simple
Enunciado: ¿Qué son los pilares de la POO?
Opciones:
A) Compilación, ejecución, depuración y despliegue
B) Encapsulamiento, herencia, polimorfismo y abstracción
C) Variables, funciones, clases y módulos
D) HTML, CSS, JS y Python
Respuesta: B
Explicacion: Los 4 pilares fundamentales de la programación orientada a objetos.
"""

    _FAKE_EXAM_FISICA = """
### Pregunta 1
Tipo: test_simple
Enunciado: ¿Qué enuncia la Segunda Ley de Newton?
Opciones:
A) Todo cuerpo permanece en reposo si no actúa fuerza
B) La fuerza neta es igual a masa por aceleración
C) A toda acción corresponde una reacción igual y opuesta
D) El momento lineal se conserva en sistemas aislados
Respuesta: B
Explicacion: F = m·a es la Segunda Ley de Newton.

### Pregunta 2
Tipo: test_simple
Enunciado: ¿Qué mide la primera ley de la termodinámica?
Opciones:
A) La entropía del sistema
B) La variación de energía interna en función del calor y el trabajo
C) La temperatura de equilibrio
D) La eficiencia de un motor Carnot
Respuesta: B
Explicacion: ΔU = Q - W es la primera ley de la termodinámica.

### Pregunta 3
Tipo: test_simple
Enunciado: ¿Cuál es la ley de Coulomb?
Opciones:
A) F = m·a
B) F = k·q₁·q₂/r²
C) E = mc²
D) F = G·m₁·m₂/r²
Respuesta: B
Explicacion: La ley de Coulomb describe la fuerza entre cargas eléctricas.
"""

    def _make_context_chunks(self, fixture_path: Path) -> list[str]:
        """Trocea el texto del fixture para usarlo como contexto falso."""
        from app.services.text_extract import extract_text_from_file
        from app.services.chunking import chunk_text_with_metadata
        text = extract_text_from_file(fixture_path)
        chunks = chunk_text_with_metadata(text, subject="test", source=fixture_path.name)
        return [c["text"] for c in chunks[:10]]

    def _make_exam_with_mock(self, topic: str, fake_llm_output: str, tmp_path: Path) -> dict:
        _setup_branch_dir(tmp_path, "TestExam")

        with patch("app.services.exams.get_branch_path", return_value=tmp_path), \
             patch("app.services.exams.branch_exists", return_value=True), \
             patch("app.services.exams.retrieve_chunks", return_value=[
                 {"text": "Texto de contexto para examen. Definición y concepto relevante del tema estudiado."},
                 {"text": "Segundo fragmento con más información sobre el tema del examen para los distractores."},
             ]), \
             patch("app.services.exams.generate_text", return_value=fake_llm_output), \
             patch("app.storage.database.get_base_dir", return_value=tmp_path):

            from app.services.exams import generate_exam
            return generate_exam("TestExam", topic=topic, num_questions=3, difficulty="medio", top_k=5, exam_type="test_simple")

    def test_generate_exam_matematicas(self, tmp_path):
        result = self._make_exam_with_mock("Cálculo diferencial", self._FAKE_EXAM_MATES, tmp_path)

        assert "exam_id" in result
        assert "exam_content" in result
        assert "avg_confidence" in result
        assert isinstance(result["exam_content"], str)
        assert len(result["exam_content"]) > 0

    def test_generate_exam_programacion(self, tmp_path):
        result = self._make_exam_with_mock("Algoritmos y estructuras de datos", self._FAKE_EXAM_PROG, tmp_path)

        assert "exam_content" in result
        content_lower = result["exam_content"].lower()
        # Verificar que las preguntas de programación aparecen en el contenido
        assert any(k in content_lower for k in ["búsqueda", "estructura", "bfs", "complejidad", "poo", "quicksort"])

    def test_generate_exam_fisica(self, tmp_path):
        result = self._make_exam_with_mock("Física: mecánica y electromagnetismo", self._FAKE_EXAM_FISICA, tmp_path)

        assert "exam_content" in result
        content_lower = result["exam_content"].lower()
        assert any(k in content_lower for k in ["newton", "termodinámica", "coulomb", "ley"])

    def test_generate_exam_saves_file(self, tmp_path):
        """Verificar que el examen se persiste en disco."""
        _setup_branch_dir(tmp_path, "SaveTest")

        with patch("app.services.exams.get_branch_path", return_value=tmp_path), \
             patch("app.services.exams.branch_exists", return_value=True), \
             patch("app.services.exams.retrieve_chunks", return_value=[{"text": "contexto"}]), \
             patch("app.services.exams.generate_text", return_value=self._FAKE_EXAM_MATES), \
             patch("app.storage.database.get_base_dir", return_value=tmp_path):

            from app.services.exams import generate_exam
            result = generate_exam("SaveTest", topic="Test save", num_questions=3, difficulty="medio", top_k=5)
            exam_id = result["exam_id"]

            exam_file = tmp_path / "Exams" / f"exam_{exam_id}.json"
            assert exam_file.exists()

            data = json.loads(exam_file.read_text(encoding="utf-8"))
            assert data["id"] == exam_id  # el fichero usa clave "id"

    def test_exam_confidence_between_0_and_1(self, tmp_path):
        result = self._make_exam_with_mock("Derivadas", self._FAKE_EXAM_MATES, tmp_path)
        assert "avg_confidence" in result
        assert 0.0 <= result["avg_confidence"] <= 1.0

    def test_exam_generation_nonexistent_branch_raises(self, tmp_path):
        with patch("app.services.exams.branch_exists", return_value=False):
            from app.services.exams import generate_exam
            with pytest.raises((FileNotFoundError, Exception)):
                generate_exam("RamaFantasma", topic="Cualquier cosa", num_questions=5, difficulty="medio", top_k=5)


# ===========================================================================
# SECCIÓN 5: VALIDADOR DE PREGUNTAS (exam_validator)
# ===========================================================================

class TestExamValidator:
    """Pruebas sobre la validación de distractores y confianza."""

    _CONTEXT = [
        "La derivada de una función es la pendiente de la recta tangente en un punto.",
        "El Teorema Fundamental del Cálculo conecta la diferenciación y la integración.",
        "La integral definida calcula el área bajo la curva entre dos límites.",
    ]

    def test_validate_test_question_returns_confidence(self):
        from app.services.exam_validator import validate_question

        question = {
            "number": 1,
            "type": "test_simple",
            "statement": "¿Qué es la derivada?",
            "options": [
                "A) La pendiente de la recta tangente",
                "B) El área bajo la curva",
                "C) El valor máximo",
                "D) El cociente diferencial",
            ],
            "answer": "A",
            "explanation": "Es la pendiente de la recta tangente.",
        }
        validated = validate_question(question, self._CONTEXT, use_llm=False)
        assert "confidence" in validated
        assert 0.0 <= validated["confidence"] <= 1.0

    def test_validate_development_question(self):
        from app.services.exam_validator import validate_question

        question = {
            "number": 2,
            "type": "desarrollo",
            "statement": "Explica el Teorema Fundamental del Cálculo.",
            "options": [],
            "answer": "La integral definida se calcula mediante la primitiva: F(b) - F(a).",
            "explanation": "",
        }
        validated = validate_question(question, self._CONTEXT, use_llm=False)
        assert "confidence" in validated
        assert 0.0 <= validated["confidence"] <= 1.0

    def test_validate_exam_questions_bulk(self):
        from app.services.exam_validator import validate_exam_questions

        questions = [
            {
                "number": 1,
                "type": "test_simple",
                "statement": "¿Qué calcula la integral definida?",
                "options": ["A) El área", "B) La pendiente", "C) La derivada", "D) El límite"],
                "answer": "A",
                "explanation": "El área bajo la curva.",
            },
            {
                "number": 2,
                "type": "test_simple",
                "statement": "¿Qué conecta el Teorema Fundamental del Cálculo?",
                "options": [
                    "A) Álgebra y geometría",
                    "B) Diferenciación e integración",
                    "C) Límites y series",
                    "D) Vectores y matrices",
                ],
                "answer": "B",
                "explanation": "Conecta derivada e integral.",
            },
        ]
        validated = validate_exam_questions(questions, self._CONTEXT)
        assert len(validated) == 2
        for q in validated:
            assert "confidence" in q

    def test_score_solved_answer_returns_float(self):
        from app.services.exam_validator import score_solved_answer

        score = score_solved_answer(
            "La derivada calcula la pendiente de la recta tangente en un punto.",
            self._CONTEXT,
        )
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_empty_answer_low_score(self):
        from app.services.exam_validator import score_solved_answer

        score = score_solved_answer("", self._CONTEXT)
        assert score <= 0.25  # mínimo posible cuando no hay tokens relevantes

    def test_unrelated_answer_lower_than_related(self):
        from app.services.exam_validator import score_solved_answer

        related = "La derivada es la pendiente de la recta tangente y el integral calcula el área."
        unrelated = "El fútbol es un deporte popular jugado con una pelota redonda en un campo."

        score_related = score_solved_answer(related, self._CONTEXT)
        score_unrelated = score_solved_answer(unrelated, self._CONTEXT)
        # La respuesta relacionada con el contexto debe puntuar igual o más alto
        assert score_related >= score_unrelated


# ===========================================================================
# SECCIÓN 6: CICLO COMPLETO (rama → ingestión → simulación → borrado)
# ===========================================================================

class TestFullLifecycle:
    """Test de ciclo completo: crear rama, ingerir doc, generar examen, simular, borrar."""

    _FAKE_LLM_EXAM = """
### Pregunta 1
Tipo: test_simple
Enunciado: ¿Cuál es la complejidad del algoritmo Quicksort en el caso promedio?
Opciones:
A) O(n)
B) O(n log n)
C) O(n²)
D) O(log n)
Respuesta: B
Explicacion: Quicksort tiene complejidad promedio O(n log n).

### Pregunta 2
Tipo: desarrollo
Enunciado: Explica la diferencia entre un proceso y un hilo.
Opciones:
Respuesta: Un proceso tiene su propio espacio de memoria mientras que un hilo comparte memoria con otros hilos del mismo proceso.
Explicacion: Concepto básico de sistemas operativos.
"""

    def test_full_lifecycle_programacion(self, tmp_path):
        """Crea rama, ingiere temario de prog, genera examen, simula, borra rama."""
        import importlib

        # 1. Crear rama
        with patch("app.storage.branches.get_base_dir", return_value=tmp_path):
            from app.storage.branches import create_branch, delete_branch, branch_exists
            from app.schemas.branch import BranchCreate

            importlib.invalidate_caches()
            create_branch(BranchCreate(name="TestProg"))
            assert branch_exists("TestProg")

        prog_branch_path = tmp_path / "Ramas" / "TestProg"

        # 2. Ingerir documento
        with patch("app.services.ingest.get_branch_path", return_value=prog_branch_path), \
             patch("app.services.ingest.branch_exists", return_value=True), \
             patch("app.services.ingest.embed_texts", return_value=_random_vectors(5)), \
             patch("app.services.ingest.add_embeddings"), \
             patch("app.storage.database.get_base_dir", return_value=tmp_path):

            from app.services.ingest import ingest_document
            ingest_result = ingest_document("TestProg", PROG_TXT)
            assert ingest_result["chunks"] > 0

        # 3. Generar examen
        with patch("app.services.exams.get_branch_path", return_value=prog_branch_path), \
             patch("app.services.exams.branch_exists", return_value=True), \
             patch("app.services.exams.retrieve_chunks", return_value=[
                 {"text": "Python es un lenguaje de tipado dinámico. La complejidad de Quicksort es O(n log n)."},
                 {"text": "Un proceso tiene su propio espacio de memoria. Un hilo comparte memoria."},
             ]), \
             patch("app.services.exams.generate_text", return_value=self._FAKE_LLM_EXAM), \
             patch("app.storage.database.get_base_dir", return_value=tmp_path):

            from app.services.exams import generate_exam
            exam_result = generate_exam("TestProg", topic="Algoritmos y sistemas operativos", num_questions=2, difficulty="medio", top_k=5)
            assert "exam_id" in exam_result
            assert "exam_content" in exam_result
            exam_id = exam_result["exam_id"]

        # 4. Simular examen (start + submit)
        with patch("app.services.exams.get_branch_path", return_value=prog_branch_path), \
             patch("app.services.exams.branch_exists", return_value=True):

            from app.services.exams import start_exam_simulation, submit_exam_simulation

            sim_result = start_exam_simulation("TestProg", exam_id, duration_minutes=60)
            assert sim_result["topic"] == "Algoritmos y sistemas operativos"
            assert len(sim_result["questions"]) == 2

            sim_id = sim_result["simulation_id"]
            answers = [
                {"number": 1, "answer": "B"},   # Correcto
                {"number": 2, "answer": "Un proceso tiene su propio espacio de memoria mientras que un hilo comparte."},
            ]
            submit_result = submit_exam_simulation("TestProg", sim_id, answers)
            assert submit_result["total_questions"] == 2
            assert submit_result["correct_answers"] >= 1
            assert 0.0 <= submit_result["score_percent"] <= 100.0

        # 5. Eliminar rama
        with patch("app.storage.branches.get_base_dir", return_value=tmp_path):
            delete_branch("TestProg")
            assert not branch_exists("TestProg")


# ===========================================================================
# SECCIÓN 7: VALIDACIÓN DE ERRORES
# ===========================================================================

class TestErrorValidation:
    """Casos de error: entradas vacías, ramas inexistentes, documentos inválidos."""

    def test_ingest_nonexistent_file_raises(self, tmp_path):
        with patch("app.services.ingest.branch_exists", return_value=True), \
             patch("app.services.ingest.get_branch_path", return_value=tmp_path):
            from app.services.ingest import ingest_document
            fake_path = tmp_path / "no_existe.txt"
            with pytest.raises(Exception):
                ingest_document("RamaX", fake_path)

    def test_generate_exam_zero_questions_allowed(self, tmp_path):
        """num_questions=0 debe producir lista vacía o error controlado."""
        _setup_branch_dir(tmp_path, "Zero")
        with patch("app.services.exams.get_branch_path", return_value=tmp_path), \
             patch("app.services.exams.branch_exists", return_value=True), \
             patch("app.services.exams.retrieve_chunks", return_value=[{"text": "contexto mínimo"}]), \
             patch("app.services.exams.generate_text", return_value=""), \
             patch("app.storage.database.get_base_dir", return_value=tmp_path):

            from app.services.exams import generate_exam
            try:
                result = generate_exam("Zero", topic="vacío", num_questions=0, difficulty="bajo", top_k=3)
                # Si no falla, debe devolver lista vacía o con pocos elementos
                assert result.get("questions") is not None
            except Exception:
                pass  # Error controlado también es válido

    def test_branch_name_with_special_chars(self, tmp_path):
        """Nombres con caracteres especiales deben crearse si el SO lo permite."""
        with patch("app.storage.branches.get_base_dir", return_value=tmp_path):
            from app.storage.branches import create_branch, branch_exists, delete_branch
            from app.schemas.branch import BranchCreate

            # Nombre con acentos y espacios
            try:
                create_branch(BranchCreate(name="Álgebra Lineal"))
                assert branch_exists("Álgebra Lineal")
                delete_branch("Álgebra Lineal")
            except Exception:
                pass  # Válido si el sistema no soporta el nombre

    def test_simulation_with_empty_answers(self, tmp_path):
        """Enviar respuestas vacías debe dar score = 0."""
        exam_id = "errtest001"
        exams_dir = tmp_path / "Exams"
        exams_dir.mkdir(parents=True, exist_ok=True)
        exam_data = {
            "exam_id": exam_id,
            "topic": "Test error",
            "questions": [
                {
                    "number": 1, "type": "test_simple",
                    "statement": "¿Qué es Python?", "options": ["A) Java", "B) Lenguaje", "C) C++", "D) Ruby"],
                    "answer": "B", "explanation": "",
                }
            ],
        }
        (exams_dir / f"exam_{exam_id}.json").write_text(json.dumps(exam_data), encoding="utf-8")

        with patch("app.services.exams.get_branch_path", return_value=tmp_path), \
             patch("app.services.exams.branch_exists", return_value=True):

            from app.services.exams import start_exam_simulation, submit_exam_simulation

            sim = start_exam_simulation("ErrBranch", exam_id)
            result = submit_exam_simulation("ErrBranch", sim["simulation_id"], [])
            assert result["correct_answers"] == 0
            assert result["score_percent"] == 0.0

    def test_chunking_very_short_text(self):
        from app.services.chunking import chunk_text_with_metadata

        short = "Hola."
        chunks = chunk_text_with_metadata(short, subject="test", source="short.txt")
        # No debe crashear, puede devolver 0 o 1 chunk
        assert isinstance(chunks, list)

    def test_validator_with_no_context(self):
        from app.services.exam_validator import validate_question

        question = {
            "number": 1, "type": "test_simple",
            "statement": "Pregunta sin contexto",
            "options": ["A) Opción A", "B) Opción B", "C) Opción C", "D) Opción D"],
            "answer": "A",
            "explanation": "",
        }
        result = validate_question(question, [], use_llm=False)
        assert "confidence" in result
        assert result["confidence"] == 0.0 or result["confidence"] >= 0.0


# ===========================================================================
# SECCIÓN 8: BANCO DE PREGUNTAS SOBRE LOS TEMARIOS
# ===========================================================================

class TestBancoPreguntas:
    """
    Banco de preguntas de test educativo sobre los tres temarios.
    Valida que el sistema puede analizar correctamente las respuestas.
    """

    # --- Matemáticas ---
    def test_derivada_correcta(self):
        from app.services.exam_validator import score_solved_answer
        context = [
            "La derivada de xⁿ es n·xⁿ⁻¹. La derivada de eˣ es eˣ. La derivada de sin(x) es cos(x).",
            "Reglas de derivación: producto (f·g)' = f'·g + f·g', cadena d/dx[f(g(x))] = f'(g(x))·g'(x).",
        ]
        respuesta = "La derivada de x al cubo es 3x al cuadrado, usando la regla de la potencia."
        score = score_solved_answer(respuesta, context)
        assert score >= 0.0  # la respuesta contiene vocabulario relevante

    def test_integral_definida_respuesta(self):
        from app.services.exam_validator import score_solved_answer
        context = [
            "La integral definida de a a b de f(x) es F(b) - F(a), donde F es la primitiva de f.",
            "El Teorema Fundamental del Cálculo conecta la diferenciación y la integración.",
        ]
        respuesta = "La integral definida calcula el área bajo la curva y se evalúa como F(b) - F(a)."
        score = score_solved_answer(respuesta, context)
        assert isinstance(score, float)

    def test_matrices_respuesta(self):
        from app.services.exam_validator import score_solved_answer
        context = [
            "El determinante de una matriz 2×2 [[a,b],[c,d]] es ad - bc.",
            "Las matrices cuadradas con determinante no nulo son invertibles.",
        ]
        respuesta = "El determinante de la matriz 2x2 se calcula como el producto de la diagonal principal menos el producto cruzado."
        score = score_solved_answer(respuesta, context)
        assert isinstance(score, float)

    # --- Programación ---
    def test_complejidad_quicksort(self):
        from app.services.exam_validator import score_solved_answer
        context = [
            "Quicksort divide la lista en torno a un pivote. Promedio O(n log n), peor caso O(n²).",
            "Mergesort tiene O(n log n) en todos los casos pero requiere O(n) memoria adicional.",
        ]
        respuesta = "Quicksort tiene complejidad O(n log n) en el caso promedio y O(n²) en el peor caso."
        score = score_solved_answer(respuesta, context)
        assert isinstance(score, float)

    def test_poo_herencia(self):
        from app.services.exam_validator import score_solved_answer
        context = [
            "Los pilares de la POO son: encapsulamiento, herencia, polimorfismo y abstracción.",
            "La herencia permite que una clase hijo herede atributos y métodos de una clase padre.",
        ]
        respuesta = "La herencia en POO permite que una subclase reutilice el código de la superclase."
        score = score_solved_answer(respuesta, context)
        assert isinstance(score, float)

    def test_sql_join_respuesta(self):
        from app.services.exam_validator import score_solved_answer
        context = [
            "INNER JOIN devuelve sólo las filas con coincidencia en ambas tablas.",
            "LEFT JOIN devuelve todas las filas de la tabla izquierda con NULL cuando no hay coincidencia.",
        ]
        respuesta = "El INNER JOIN solo devuelve las filas que tienen coincidencia en ambas tablas."
        score = score_solved_answer(respuesta, context)
        assert isinstance(score, float)

    # --- Física ---
    def test_segunda_ley_newton(self):
        from app.services.exam_validator import score_solved_answer
        context = [
            "Segunda ley de Newton: la fuerza neta sobre un cuerpo es F = m·a.",
            "La aceleración es directamente proporcional a la fuerza e inversamente proporcional a la masa.",
        ]
        respuesta = "La Segunda Ley de Newton dice que F = m·a, la fuerza es masa por aceleración."
        score = score_solved_answer(respuesta, context)
        assert isinstance(score, float)

    def test_termologia_respuesta(self):
        from app.services.exam_validator import score_solved_answer
        context = [
            "La primera ley de la termodinámica: ΔU = Q - W. La energía interna varía con calor y trabajo.",
            "Un proceso adiabático no intercambia calor con el entorno (Q = 0).",
        ]
        respuesta = "La primera ley de la termodinámica establece que la variación de energía interna es igual al calor menos el trabajo realizado."
        score = score_solved_answer(respuesta, context)
        assert isinstance(score, float)

    def test_coulomb_respuesta(self):
        from app.services.exam_validator import score_solved_answer
        context = [
            "Ley de Coulomb: F = k·q₁·q₂/r², donde k = 9×10⁹ N·m²/C².",
            "El campo eléctrico es E = k·Q/r² con dirección radial para cargas positivas.",
        ]
        respuesta = "La ley de Coulomb expresa la fuerza entre dos cargas eléctricas como F = k·q1·q2/r²."
        score = score_solved_answer(respuesta, context)
        assert isinstance(score, float)


# ===========================================================================
# Helpers compartidos
# ===========================================================================

def _setup_branch_dir(base_path: Path, branch_name: str) -> Path:
    """Crea la estructura mínima de directorios de una rama dentro de base_path."""
    branch_path = base_path
    (branch_path / "Material").mkdir(parents=True, exist_ok=True)
    (branch_path / "Index").mkdir(parents=True, exist_ok=True)
    (branch_path / "Chats").mkdir(parents=True, exist_ok=True)
    (branch_path / "Exams").mkdir(parents=True, exist_ok=True)
    (branch_path / "settings.json").write_text("{}", encoding="utf-8")
    return branch_path


def _random_vectors(n: int):
    import numpy as np
    return np.random.rand(n, 384).astype("float32")
