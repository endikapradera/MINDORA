import type {
  AskResponse,
  Branch,
  ChatSession,
  DictionaryEntry,
  DictionaryResponse,
  DailyRecommendationsResponse,
  ExamSolveUploadResponse,
  ExamSimulationStartResponse,
  ExamSimulationSubmitResponse,
  ExamSimulationHistoryResponse,
  ExamType,
  ExportKind,
  ExamExportResponse,
  ExamGenerateResponse,
  QueryResponse,
  StudyPackResponse,
  DocumentListResponse,
  ResponseStyle,
  LearnPhrasePayload,
  FeedbackPayload
} from "./types";

const BASE_URL = "http://127.0.0.1:8000";

async function toApiError(res: Response, fallback: string): Promise<Error> {
  let detail = fallback;
  try {
    const payload = await res.json();
    if (typeof payload?.detail === "string" && payload.detail.trim().length > 0) {
      detail = payload.detail;
    } else if (Array.isArray(payload?.detail) && payload.detail.length > 0) {
      const first = payload.detail[0];
      if (typeof first?.msg === "string" && first.msg.trim().length > 0) {
        detail = first.msg;
      }
    }
  } catch {
    // ignore json parse failures
  }
  return new Error(detail);
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE_URL}/health`, { signal: AbortSignal.timeout(1500) });
    return res.ok;
  } catch {
    return false;
  }
}

export async function getSetupStatus(): Promise<{
  model_found: boolean;
  model_path: string | null;
  expected_dir: string;
  gguf_files: string[];
}> {
  const res = await fetch(`${BASE_URL}/api/setup/status`);
  if (!res.ok) throw new Error("Error checking setup");
  return res.json();
}

export async function fetchBranches(): Promise<Branch[]> {
  const res = await fetch(`${BASE_URL}/api/branches`);
  if (!res.ok) throw await toApiError(res, "Error cargando ramas");
  return res.json();
}

export async function createBranch(name: string): Promise<Branch> {
  const res = await fetch(`${BASE_URL}/api/branches`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name })
  });
  if (!res.ok) throw await toApiError(res, "Error creando rama");
  return res.json();
}

export async function deleteBranch(name: string): Promise<{ status: string }> {
  const res = await fetch(`${BASE_URL}/api/branches?name=${encodeURIComponent(name)}`, {
    method: "DELETE"
  });
  if (!res.ok) throw await toApiError(res, "Error eliminando rama");
  return res.json();
}

export async function ingestDocument(
  branch: string,
  file: File,
  onProgress?: (percent: number) => void
): Promise<{ document_id: number; chunks: number }> {
  const form = new FormData();
  form.append("branch", branch);
  form.append("file", file);

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${BASE_URL}/api/documents/ingest`);

    xhr.upload.addEventListener("progress", (event) => {
      if (!event.lengthComputable) return;
      const percent = Math.round((event.loaded / event.total) * 100);
      onProgress?.(Math.max(0, Math.min(100, percent)));
    });

    xhr.onreadystatechange = () => {
      if (xhr.readyState !== XMLHttpRequest.DONE) return;

      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const payload = JSON.parse(xhr.responseText) as { document_id: number; chunks: number };
          onProgress?.(100);
          resolve(payload);
        } catch {
          reject(new Error("Respuesta inválida en la ingesta"));
        }
        return;
      }

      try {
        const payload = JSON.parse(xhr.responseText) as { detail?: string };
        reject(new Error(payload.detail || "Error en ingesta"));
      } catch {
        reject(new Error("Error en ingesta"));
      }
    };

    xhr.onerror = () => reject(new Error("No se pudo conectar con el servidor durante la ingesta"));
    xhr.send(form);
  });
}

export async function queryRag(branch: string, question: string, topK: number, documentId?: number): Promise<QueryResponse> {
  const res = await fetch(`${BASE_URL}/api/query?branch=${encodeURIComponent(branch)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, top_k: topK, document_id: documentId ?? null })
  });
  if (!res.ok) throw await toApiError(res, "Error en query");
  return res.json();
}

export async function askRag(
  branch: string,
  question: string,
  topK: number,
  responseStyle: ResponseStyle,
  sessionId?: string,
  documentId?: number
): Promise<AskResponse> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 90_000);
  const res = await fetch(`${BASE_URL}/api/ask?branch=${encodeURIComponent(branch)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, top_k: topK, response_style: responseStyle, session_id: sessionId ?? null, document_id: documentId ?? null }),
    signal: controller.signal,
  });
  clearTimeout(timeout);
  if (!res.ok) throw await toApiError(res, "Error en ask");
  return res.json();
}

export async function learnPhrase(payload: LearnPhrasePayload): Promise<{ status: string }> {
  const res = await fetch(`${BASE_URL}/api/assistant/learn-phrase`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error("Error guardando frase");
  return res.json();
}

export async function sendFeedback(payload: FeedbackPayload): Promise<{ status: string }> {
  const res = await fetch(`${BASE_URL}/api/assistant/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error("Error enviando feedback");
  return res.json();
}

export async function generateExam(
  branch: string,
  topic: string,
  numQuestions: number,
  difficulty: string,
  topK: number,
  examType: ExamType
): Promise<ExamGenerateResponse> {
  const res = await fetch(`${BASE_URL}/api/exams/generate?branch=${encodeURIComponent(branch)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic, num_questions: numQuestions, difficulty, top_k: topK, exam_type: examType })
  });
  if (!res.ok) throw await toApiError(res, "Error generando examen");
  return res.json();
}

export async function exportExamPdf(
  branch: string,
  examId: string,
  kind: ExportKind = "exam"
): Promise<ExamExportResponse> {
  const res = await fetch(
    `${BASE_URL}/api/exams/export/pdf?branch=${encodeURIComponent(branch)}&exam_id=${encodeURIComponent(examId)}&kind=${encodeURIComponent(kind)}`,
    { method: "POST" }
  );
  if (!res.ok) throw new Error("Error exportando PDF");
  return res.json();
}

export async function exportExamDocx(
  branch: string,
  examId: string,
  kind: ExportKind = "exam"
): Promise<ExamExportResponse> {
  const res = await fetch(
    `${BASE_URL}/api/exams/export/docx?branch=${encodeURIComponent(branch)}&exam_id=${encodeURIComponent(examId)}&kind=${encodeURIComponent(kind)}`,
    { method: "POST" }
  );
  if (!res.ok) throw new Error("Error exportando DOCX");
  return res.json();
}

export async function solveUploadedExam(
  branch: string,
  file: File,
  topK = 8
): Promise<ExamSolveUploadResponse> {
  const form = new FormData();
  form.append("branch", branch);
  form.append("file", file);
  form.append("top_k", String(topK));

  const res = await fetch(`${BASE_URL}/api/exams/solve-upload`, {
    method: "POST",
    body: form
  });
  if (!res.ok) throw new Error("Error resolviendo examen");
  return res.json();
}

export async function startExamSimulation(
  branch: string,
  examId: string,
  durationMinutes: number
): Promise<ExamSimulationStartResponse> {
  const res = await fetch(`${BASE_URL}/api/exams/simulation/start?branch=${encodeURIComponent(branch)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ exam_id: examId, duration_minutes: durationMinutes })
  });
  if (!res.ok) throw new Error("Error iniciando simulacro");
  return res.json();
}

export async function submitExamSimulation(
  branch: string,
  simulationId: string,
  answers: Array<{ number: number; answer: string }>
): Promise<ExamSimulationSubmitResponse> {
  const res = await fetch(`${BASE_URL}/api/exams/simulation/submit?branch=${encodeURIComponent(branch)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ simulation_id: simulationId, answers })
  });
  if (!res.ok) throw new Error("Error entregando simulacro");
  return res.json();
}

export async function getSimulationHistory(branch: string, limit = 30): Promise<ExamSimulationHistoryResponse> {
  const res = await fetch(
    `${BASE_URL}/api/exams/simulation/history?branch=${encodeURIComponent(branch)}&limit=${limit}`
  );
  if (!res.ok) throw new Error("Error cargando historial de simulacros");
  return res.json();
}

export async function listDocuments(branch: string): Promise<DocumentListResponse> {
  const res = await fetch(`${BASE_URL}/api/documents?branch=${encodeURIComponent(branch)}`);
  if (!res.ok) throw await toApiError(res, "Error listando documentos");
  return res.json();
}

export async function generateStudyPack(branch: string, topic: string, topK = 6): Promise<StudyPackResponse> {
  const res = await fetch(`${BASE_URL}/api/study/topic-pack?branch=${encodeURIComponent(branch)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic, top_k: topK })
  });
  if (!res.ok) throw new Error("Error generando pack de estudio");
  return res.json();
}

export async function getDailyRecommendations(branch: string): Promise<DailyRecommendationsResponse> {
  const res = await fetch(
    `${BASE_URL}/api/study/daily-recommendations?branch=${encodeURIComponent(branch)}`
  );
  if (!res.ok) throw new Error("Error cargando recomendaciones");
  return res.json();
}

export async function listDictionary(): Promise<DictionaryResponse> {
  const res = await fetch(`${BASE_URL}/api/assistant/dictionary`);
  if (!res.ok) throw new Error("Error cargando diccionario");
  return res.json();
}

export async function listCustomDictionary(): Promise<DictionaryResponse> {
  const res = await fetch(`${BASE_URL}/api/assistant/dictionary/custom`);
  if (!res.ok) throw new Error("Error cargando diccionario personalizado");
  return res.json();
}

export async function removeDictionaryPhrase(phrase: string): Promise<{ status: string }> {
  const res = await fetch(
    `${BASE_URL}/api/assistant/dictionary?phrase=${encodeURIComponent(phrase)}`,
    { method: "DELETE" }
  );
  if (!res.ok) throw new Error("Error eliminando frase");
  return res.json();
}

// ── Chat session history ──────────────────────────────────────────────────────

export async function listChatSessions(branch: string, query?: string): Promise<ChatSession[]> {
  const q = query && query.trim().length > 0 ? `?q=${encodeURIComponent(query.trim())}` : "";
  const res = await fetch(`${BASE_URL}/api/chats/${encodeURIComponent(branch)}${q}`);
  if (!res.ok) throw await toApiError(res, "Error cargando historial de sesiones");
  return res.json();
}

export async function loadChatSession(
  branch: string,
  sessionId: string
): Promise<{ session_id: string; messages: { role: string; content: string }[] }> {
  const res = await fetch(
    `${BASE_URL}/api/chats/${encodeURIComponent(branch)}/${encodeURIComponent(sessionId)}`
  );
  if (!res.ok) throw await toApiError(res, "Error cargando sesión");
  return res.json();
}

export async function deleteChatSession(
  branch: string,
  sessionId: string
): Promise<{ status: string }> {
  const res = await fetch(
    `${BASE_URL}/api/chats/${encodeURIComponent(branch)}/${encodeURIComponent(sessionId)}`,
    { method: "DELETE" }
  );
  if (!res.ok) throw await toApiError(res, "Error eliminando sesión");
  return res.json();
}

export async function renameChatSession(
  branch: string,
  sessionId: string,
  title: string
): Promise<{ status: string; title: string }> {
  const res = await fetch(
    `${BASE_URL}/api/chats/${encodeURIComponent(branch)}/${encodeURIComponent(sessionId)}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    }
  );
  if (!res.ok) throw await toApiError(res, "Error renombrando sesión");
  return res.json();
}

export async function pinChatSession(
  branch: string,
  sessionId: string,
  pinned: boolean
): Promise<{ status: string; pinned: boolean }> {
  const res = await fetch(
    `${BASE_URL}/api/chats/${encodeURIComponent(branch)}/${encodeURIComponent(sessionId)}/pin`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pinned }),
    }
  );
  if (!res.ok) throw await toApiError(res, "Error fijando sesión");
  return res.json();
}
