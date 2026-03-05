import { useEffect, useMemo, useState } from "react";
import type { ChangeEvent } from "react";
import {
  askRag,
  createBranch,
  exportExamDocx,
  exportExamPdf,
  fetchBranches,
  generateExam,
  ingestDocument,
  queryRag
} from "./api";
import type { Branch } from "./types";

export default function App() {
  const [branches, setBranches] = useState<Branch[]>([]);
  const [branchName, setBranchName] = useState("");
  const [selectedBranch, setSelectedBranch] = useState<string>("");
  const [file, setFile] = useState<File | null>(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [contexts, setContexts] = useState<string[]>([]);
  const [chunks, setChunks] = useState<string[]>([]);
  const [examTopic, setExamTopic] = useState("");
  const [examDifficulty, setExamDifficulty] = useState("media");
  const [examCount, setExamCount] = useState(10);
  const [examId, setExamId] = useState("");
  const [examContent, setExamContent] = useState("");
  const [status, setStatus] = useState("");

  const canUseBranch = useMemo(() => selectedBranch.length > 0, [selectedBranch]);

  useEffect(() => {
    loadBranches();
  }, []);

  async function loadBranches() {
    try {
      const data = await fetchBranches();
      setBranches(data);
      if (data.length > 0 && !selectedBranch) {
        setSelectedBranch(data[0].name);
      }
    } catch (err) {
      setStatus("No se pudo cargar ramas. Asegura que el core esté activo.");
    }
  }

  async function handleCreateBranch() {
    if (!branchName) return;
    try {
      const created = await createBranch(branchName);
      setBranches((prev: Branch[]) => [...prev, created]);
      setSelectedBranch(created.name);
      setBranchName("");
      setStatus("Rama creada");
    } catch {
      setStatus("Error creando rama");
    }
  }

  async function handleIngest() {
    if (!file || !canUseBranch) return;
    try {
      const result = await ingestDocument(selectedBranch, file);
      setStatus(`Documento ingresado. Chunks: ${result.chunks}`);
    } catch {
      setStatus("Error en ingesta");
    }
  }

  async function handleQuery() {
    if (!question || !canUseBranch) return;
    try {
      const result = await queryRag(selectedBranch, question, 5);
      setChunks(result.results.map((r) => r.text));
      setStatus(`Resultados: ${result.results.length}`);
    } catch {
      setStatus("Error en query");
    }
  }

  async function handleAsk() {
    if (!question || !canUseBranch) return;
    try {
      const result = await askRag(selectedBranch, question, 5);
      setAnswer(result.answer);
      setContexts(result.contexts);
      setStatus("Respuesta generada");
    } catch {
      setStatus("Error en ask");
    }
  }

  async function handleExam() {
    if (!examTopic || !canUseBranch) return;
    try {
      const result = await generateExam(selectedBranch, examTopic, examCount, examDifficulty, 6);
      setExamId(result.exam_id);
      setExamContent(result.content);
      setStatus("Examen generado");
    } catch {
      setStatus("Error generando examen");
    }
  }

  async function handleExportPdf() {
    if (!examId || !canUseBranch) return;
    try {
      const result = await exportExamPdf(selectedBranch, examId);
      setStatus(`PDF exportado: ${result.path}`);
    } catch {
      setStatus("Error exportando PDF");
    }
  }

  async function handleExportDocx() {
    if (!examId || !canUseBranch) return;
    try {
      const result = await exportExamDocx(selectedBranch, examId);
      setStatus(`DOCX exportado: ${result.path}`);
    } catch {
      setStatus("Error exportando DOCX");
    }
  }

  return (
    <div className="container">
      <div className="header">
        <div>
          <h1>IA Educativa Offline</h1>
          <span className="badge">Core local + RAG + Exámenes</span>
        </div>
        <div className="row">
          <select
            value={selectedBranch}
            onChange={(e: ChangeEvent<HTMLSelectElement>) => setSelectedBranch(e.target.value)}
          >
            <option value="">Selecciona rama</option>
            {branches.map((b: Branch) => (
              <option key={b.name} value={b.name}>
                {b.name}
              </option>
            ))}
          </select>
          <button onClick={loadBranches}>Refrescar</button>
        </div>
      </div>

      <div className="grid">
        <div className="card">
          <h3>Crear rama</h3>
          <input
            placeholder="Nombre de la rama"
            value={branchName}
            onChange={(e: ChangeEvent<HTMLInputElement>) => setBranchName(e.target.value)}
          />
          <button onClick={handleCreateBranch}>Crear</button>
        </div>

        <div className="card">
          <h3>Ingesta de documentos</h3>
          <input
            type="file"
            onChange={(e: ChangeEvent<HTMLInputElement>) => setFile(e.target.files?.[0] ?? null)}
          />
          <button onClick={handleIngest} disabled={!file || !canUseBranch}>
            Ingestar
          </button>
        </div>

        <div className="card">
          <h3>Pregunta (RAG)</h3>
          <textarea
            rows={4}
            placeholder="Escribe tu pregunta"
            value={question}
            onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setQuestion(e.target.value)}
          />
          <div className="row">
            <button onClick={handleQuery} disabled={!canUseBranch}>
              Ver contexto
            </button>
            <button onClick={handleAsk} disabled={!canUseBranch}>
              Responder
            </button>
          </div>
        </div>

        <div className="card">
          <h3>Generar examen</h3>
          <input
            placeholder="Tema"
            value={examTopic}
            onChange={(e: ChangeEvent<HTMLInputElement>) => setExamTopic(e.target.value)}
          />
          <div className="row">
            <input
              type="number"
              min={1}
              max={50}
              value={examCount}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setExamCount(Number(e.target.value))}
            />
            <select
              value={examDifficulty}
              onChange={(e: ChangeEvent<HTMLSelectElement>) => setExamDifficulty(e.target.value)}
            >
              <option value="baja">Baja</option>
              <option value="media">Media</option>
              <option value="alta">Alta</option>
            </select>
          </div>
          <button onClick={handleExam} disabled={!canUseBranch}>
            Generar
          </button>
          <div className="row">
            <button onClick={handleExportPdf} disabled={!examId || !canUseBranch}>
              Exportar PDF
            </button>
            <button onClick={handleExportDocx} disabled={!examId || !canUseBranch}>
              Exportar DOCX
            </button>
          </div>
        </div>
      </div>

      <div className="card">
        <h3>Estado</h3>
        <p>{status || "Sin acciones aún"}</p>
      </div>

      {chunks.length > 0 && (
        <div className="card">
          <h3>Contextos</h3>
          {chunks.map((c, idx) => (
            <div key={idx} className="result">
              {c}
            </div>
          ))}
        </div>
      )}

      {answer && (
        <div className="card">
          <h3>Respuesta</h3>
          <div className="result">{answer}</div>
        </div>
      )}

      {examContent && (
        <div className="card">
          <h3>Examen</h3>
          <div className="result">{examContent}</div>
        </div>
      )}

      {contexts.length > 0 && (
        <div className="card">
          <h3>Contexto usado</h3>
          {contexts.map((c, idx) => (
            <div key={idx} className="result">
              {c}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
