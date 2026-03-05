import type {
  AskResponse,
  Branch,
  ExamExportResponse,
  ExamGenerateResponse,
  QueryResponse
} from "./types";

const BASE_URL = "http://127.0.0.1:8000";

export async function fetchBranches(): Promise<Branch[]> {
  const res = await fetch(`${BASE_URL}/api/branches`);
  if (!res.ok) throw new Error("Error cargando ramas");
  return res.json();
}

export async function createBranch(name: string): Promise<Branch> {
  const res = await fetch(`${BASE_URL}/api/branches`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name })
  });
  if (!res.ok) throw new Error("Error creando rama");
  return res.json();
}

export async function ingestDocument(branch: string, file: File): Promise<{ document_id: number; chunks: number }> {
  const form = new FormData();
  form.append("branch", branch);
  form.append("file", file);

  const res = await fetch(`${BASE_URL}/api/documents/ingest`, {
    method: "POST",
    body: form
  });
  if (!res.ok) throw new Error("Error en ingesta");
  return res.json();
}

export async function queryRag(branch: string, question: string, topK: number): Promise<QueryResponse> {
  const res = await fetch(`${BASE_URL}/api/query?branch=${encodeURIComponent(branch)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, top_k: topK })
  });
  if (!res.ok) throw new Error("Error en query");
  return res.json();
}

export async function askRag(branch: string, question: string, topK: number): Promise<AskResponse> {
  const res = await fetch(`${BASE_URL}/api/ask?branch=${encodeURIComponent(branch)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, top_k: topK })
  });
  if (!res.ok) throw new Error("Error en ask");
  return res.json();
}

export async function generateExam(
  branch: string,
  topic: string,
  numQuestions: number,
  difficulty: string,
  topK: number
): Promise<ExamGenerateResponse> {
  const res = await fetch(`${BASE_URL}/api/exams/generate?branch=${encodeURIComponent(branch)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic, num_questions: numQuestions, difficulty, top_k: topK })
  });
  if (!res.ok) throw new Error("Error generando examen");
  return res.json();
}

export async function exportExamPdf(branch: string, examId: string): Promise<ExamExportResponse> {
  const res = await fetch(
    `${BASE_URL}/api/exams/export/pdf?branch=${encodeURIComponent(branch)}&exam_id=${encodeURIComponent(examId)}`,
    { method: "POST" }
  );
  if (!res.ok) throw new Error("Error exportando PDF");
  return res.json();
}

export async function exportExamDocx(branch: string, examId: string): Promise<ExamExportResponse> {
  const res = await fetch(
    `${BASE_URL}/api/exams/export/docx?branch=${encodeURIComponent(branch)}&exam_id=${encodeURIComponent(examId)}`,
    { method: "POST" }
  );
  if (!res.ok) throw new Error("Error exportando DOCX");
  return res.json();
}
