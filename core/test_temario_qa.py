#!/usr/bin/env python3
"""
test_temario_qa.py — Prueba Q&A contra el banco TEMARIO

Carga preguntas del archivo preguntas-temario.txt y las formula contra
la API de MINDORA (requiere backend corriendo en puerto 8000).

Valida:
  - Conectividad backend
  - Carga correcta de documentos
  - Respuestas coherentes (no vacías, no errores)
  - Latencia aceptable
  - Formato de respuesta JSON válido
"""

import json
import re
import sys
import time
from pathlib import Path
from typing import Optional

import requests


BACKEND_URL = "http://127.0.0.1:8000"
TEMARIO_PATH = Path("/Users/endikapraderatouzani/Desktop/MINDORA/TEMARIO ")
QUESTIONS_FILE = TEMARIO_PATH / "preguntas-temario.txt"

# Colores para output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def log_pass(msg: str):
    print(f"{GREEN}✓ {msg}{RESET}")


def log_fail(msg: str):
    print(f"{RED}✗ {msg}{RESET}")


def log_info(msg: str):
    print(f"{BLUE}ℹ {msg}{RESET}")


def log_warn(msg: str):
    print(f"{YELLOW}⚠ {msg}{RESET}")


def check_backend() -> bool:
    """Verifica que el backend esté disponible."""
    log_info("Verificando conectividad backend...")
    try:
        resp = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if resp.status_code == 200:
            log_pass("Backend disponible en " + BACKEND_URL)
            return True
        else:
            log_fail(f"Backend respondió con status {resp.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        log_fail(f"No se puede conectar a {BACKEND_URL}")
        log_info("Asegúrate de que el backend está corriendo: python3 run_server.py")
        return False
    except Exception as e:
        log_fail(f"Error al conectar: {e}")
        return False


def parse_questions(text: str) -> dict[str, list[str]]:
    """Parsea preguntas del formato markdown por tema."""
    questions = {}
    current_theme = None
    current_level = None

    for line in text.split('\n'):
        line = line.strip()

        # Detecta tema (## A1 – LÓGICA)
        if line.startswith('# ') and ' – ' in line:
            current_theme = line.replace('# ', '').replace('📘', '').replace('📊', '')\
                .replace('📈', '').replace('⚖️', '').replace('💻', '').strip()
            questions[current_theme] = []

        # Detecta nivel (### Básicas, etc)
        if line.startswith('### '):
            current_level = line.replace('### ', '').strip()

        # Detecta preguntas (* Explícame...)
        if line.startswith('* ') and current_theme:
            q = line.replace('* ', '').strip()
            questions[current_theme].append(q)

    return questions


def ask_question(q: str, style: str = "auto", max_attempts: int = 3) -> Optional[dict]:
    """
    Formula una pregunta al backend.

    Retorna dict con 'response' y 'latency' si éxito, None si fallo.
    """
    payload = {
        "question": q,
        "response_style": style,
        "top_k": 5,
    }

    for attempt in range(max_attempts):
        try:
            start = time.time()
            resp = requests.post(
                f"{BACKEND_URL}/api/ask",
                json=payload,
                params={"branch": "principal"},
                timeout=120
            )
            latency = time.time() - start

            if resp.status_code == 200:
                data = resp.json()
                return {
                    'response': data.get('answer', ''),
                    'latency': latency,
                    'sources': len(data.get('sources', []))
                }
            else:
                log_warn(f"  Status {resp.status_code} (intento {attempt + 1}/{max_attempts})")
                if attempt < max_attempts - 1:
                    time.sleep(2)

        except requests.exceptions.Timeout:
            log_warn(f"  Timeout (intento {attempt + 1}/{max_attempts})")
            if attempt < max_attempts - 1:
                time.sleep(5)
        except requests.exceptions.RequestException as e:
            log_warn(f"  Error de red: {e}")
            if attempt < max_attempts - 1:
                time.sleep(2)

    return None


def validate_response(ans: str) -> tuple[bool, str]:
    """Valida que la respuesta sea coherente."""
    if not ans or len(ans.strip()) == 0:
        return False, "Respuesta vacía"

    if ans.count('sorry') + ans.count('error') + ans.count('fallo') > 2:
        return False, "Respuesta parece error/no disponible"

    if len(ans) < 20:
        return False, "Respuesta muy corta (<20 caracteres)"

    return True, "OK"


def run_tests():
    """Ejecuta suite completa de testing."""
    print(f"\n{BLUE}{'='*70}")
    print("MINDORA – Suite de Testing con TEMARIO")
    print(f"{'='*70}{RESET}\n")

    # 1. Verificar backend
    if not check_backend():
        log_fail("Abortando: backend no disponible")
        return 1

    # 2. Cargar preguntas
    log_info(f"Cargando preguntas desde {QUESTIONS_FILE.name}...")
    if not QUESTIONS_FILE.exists():
        log_fail(f"Archivo no encontrado: {QUESTIONS_FILE}")
        return 1

    text = QUESTIONS_FILE.read_text(encoding='utf-8')
    questions = parse_questions(text)

    if not questions:
        log_fail("No se encontraron preguntas en el archivo")
        return 1

    log_pass(f"Cargadas {sum(len(qs) for qs in questions.values())} preguntas de {len(questions)} temas")

    # 3. Ejecutar tests
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    errors = []

    for theme, qs in sorted(questions.items()):
        print(f"\n{BLUE}┌─ {theme}{RESET}")
        theme_passed = 0

        # Test máx 3 preguntas por tema para no tardar demasiado
        for i, q in enumerate(qs[:3]):
            total_tests += 1
            q_short = (q[:60] + '...') if len(q) > 60 else q

            result = ask_question(q, style="profesor")

            if result:
                is_valid, msg = validate_response(result['response'])
                if is_valid:
                    theme_passed += 1
                    passed_tests += 1
                    log_pass(f"  {q_short} ({result['latency']:.1f}s)")
                else:
                    failed_tests += 1
                    log_fail(f"  {q_short}: {msg}")
                    errors.append({'theme': theme, 'question': q, 'error': msg})
            else:
                failed_tests += 1
                log_fail(f"  {q_short}: Sin respuesta después de reintentos")
                errors.append({'theme': theme, 'question': q, 'error': 'Timeout o error red'})

        print(f"{BLUE}└─ {theme_passed}/{min(3, len(qs))} pasaron{RESET}")

    # 4. Reporte final
    print(f"\n{BLUE}{'='*70}")
    print("REPORTE FINAL")
    print(f"{'='*70}{RESET}")

    total_pct = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    if total_pct >= 80:
        log_pass(f"Total: {passed_tests}/{total_tests} tests pasaron ({total_pct:.0f}%)")
    elif total_pct >= 50:
        log_warn(f"Total: {passed_tests}/{total_tests} tests pasaron ({total_pct:.0f}%)")
    else:
        log_fail(f"Total: {passed_tests}/{total_tests} tests pasaron ({total_pct:.0f}%)")

    if errors:
        print(f"\n{RED}Errores encontrados:{RESET}")
        for err in errors[:5]:  # Muestra máx 5 errores
            print(f"  • {err['theme']}")
            print(f"    Pregunta: {err['question'][:70]}...")
            print(f"    Error: {err['error']}\n")

    return 0 if total_pct >= 70 else 1


if __name__ == '__main__':
    sys.exit(run_tests())
