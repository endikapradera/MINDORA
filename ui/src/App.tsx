import { useEffect, useMemo, useState } from "react";
import type { ChangeEvent } from "react";
import {
  askRag,
  createBranch,
  deleteBranch,
  exportExamDocx,
  exportExamPdf,
  fetchBranches,
  checkHealth,
  getSetupStatus,
  generateStudyPack,
  getDailyRecommendations,
  getSimulationHistory,
  generateExam,
  ingestDocument,
  learnPhrase,
  listCustomDictionary,
  listDocuments,
  removeDictionaryPhrase,
  solveUploadedExam,
  startExamSimulation,
  submitExamSimulation,
  sendFeedback,
  queryRag
} from "./api";
import type {
  Branch,
  DailyRecommendationItem,
  DictionaryEntry,
  DocumentItem,
  ResponseStyle,
  ExamType,
  SimulationQuestion,
  ExamSimulationSubmitResponse,
  ExamSimulationHistoryItem
} from "./types";

function styleLabel(style: ResponseStyle): string {
  if (style === "auto") return "Auto";
  if (style === "corta") return "Corta";
  if (style === "detallada") return "Detallada";
  if (style === "pasos") return "Por pasos";
  if (style === "examen") return "Modo examen";
  if (style === "profesor") return "Modo profesor";
  if (style === "companero") return "Modo compañero";
  return "Detallada por pasos";
}

function formatSeconds(totalSeconds: number): string {
  const seconds = Math.max(0, totalSeconds);
  const m = Math.floor(seconds / 60)
    .toString()
    .padStart(2, "0");
  const s = Math.floor(seconds % 60)
    .toString()
    .padStart(2, "0");
  return `${m}:${s}`;
}

type AppSection = "dashboard" | "temarios" | "estudiar" | "examenes" | "progreso" | "config";

export default function App() {
  const [showSplash, setShowSplash] = useState(true);
  const [showInfoModal, setShowInfoModal] = useState(false);
  const [branches, setBranches] = useState<Branch[]>([]);
  // ── Backend readiness ──────────────────────────────────────────────────
  const [backendReady, setBackendReady] = useState(false);
  const [backendLoadingDots, setBackendLoadingDots] = useState("");
  const [modelFound, setModelFound] = useState<boolean | null>(null);
  const [modelExpectedDir, setModelExpectedDir] = useState("");
  // ──────────────────────────────────────────────────────────────────────
  const [branchName, setBranchName] = useState("");
  const [selectedBranch, setSelectedBranch] = useState<string>("");
  const [file, setFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedStudyDocumentId, setSelectedStudyDocumentId] = useState<number | "all">("all");
  const [question, setQuestion] = useState("");
  const [responseStyle, setResponseStyle] = useState<ResponseStyle>("auto");
  const [quickAction, setQuickAction] = useState<"facil" | "examen" | "ejemplos" | "pasos" | "minuto">("facil");
  const [lastAnswerStyle, setLastAnswerStyle] = useState<ResponseStyle | null>(null);
  const [lastQuestion, setLastQuestion] = useState("");
  const [sessionId, setSessionId] = useState<string>(crypto.randomUUID());
  const [answer, setAnswer] = useState("");
  const [learnPhraseText, setLearnPhraseText] = useState("");
  const [contexts, setContexts] = useState<string[]>([]);
  const [sources, setSources] = useState<string[]>([]);
  const [chunks, setChunks] = useState<string[]>([]);
  const [examTopic, setExamTopic] = useState("");
  const [examDifficulty, setExamDifficulty] = useState("media");
  const [examType, setExamType] = useState<ExamType>("mixto");
  const [examCount, setExamCount] = useState(10);
  const [retrievalDepth, setRetrievalDepth] = useState(6);
  const [examQualityMode, setExamQualityMode] = useState<"rapido" | "equilibrado" | "maximo">("equilibrado");
  const [examId, setExamId] = useState("");
  const [examAvgConfidence, setExamAvgConfidence] = useState<number | null>(null);
  const [examWarnings, setExamWarnings] = useState<string[]>([]);
  const [examContent, setExamContent] = useState("");
  const [answerKeyContent, setAnswerKeyContent] = useState("");
  const [examSolveFile, setExamSolveFile] = useState<File | null>(null);
  const [solvedExamContent, setSolvedExamContent] = useState("");
  const [solvedExamConfidence, setSolvedExamConfidence] = useState<number | null>(null);
  const [simulationDuration, setSimulationDuration] = useState(30);
  const [simulationId, setSimulationId] = useState("");
  const [simulationQuestions, setSimulationQuestions] = useState<SimulationQuestion[]>([]);
  const [simulationAnswers, setSimulationAnswers] = useState<Record<number, string>>({});
  const [simulationExpiresAt, setSimulationExpiresAt] = useState<string | null>(null);
  const [simulationTimeLeft, setSimulationTimeLeft] = useState(0);
  const [simulationResult, setSimulationResult] = useState<ExamSimulationSubmitResponse | null>(null);
  const [simulationHistory, setSimulationHistory] = useState<ExamSimulationHistoryItem[]>([]);
  const [isAutoSubmittingSimulation, setIsAutoSubmittingSimulation] = useState(false);
  const [studySummaryShort, setStudySummaryShort] = useState("");
  const [studySummaryLong, setStudySummaryLong] = useState("");
  const [studyIdeas, setStudyIdeas] = useState<string[]>([]);
  const [studyConcepts, setStudyConcepts] = useState<string[]>([]);
  const [studyExamQuestions, setStudyExamQuestions] = useState<string[]>([]);
  const [studyMistakes, setStudyMistakes] = useState<string[]>([]);
  const [studyMiniTest, setStudyMiniTest] = useState<string[]>([]);
  const [studySources, setStudySources] = useState<string[]>([]);
  const [status, setStatus] = useState("");
  const [toast, setToast] = useState<{msg: string; type: "ok"|"err"} | null>(null);
  // Inline validation errors por formulario
  const [branchNameError, setBranchNameError] = useState("");
  const [fileError, setFileError] = useState("");
  const [questionError, setQuestionError] = useState("");
  const [examTopicError, setExamTopicError] = useState("");
  const [learnPhraseError, setLearnPhraseError] = useState("");
  const [dictEntries, setDictEntries] = useState<DictionaryEntry[]>([]);
  const [showDictPanel, setShowDictPanel] = useState(false);
  const [dailyRecs, setDailyRecs] = useState<DailyRecommendationItem[]>([]);
  const [dailyRecsMsg, setDailyRecsMsg] = useState("");
  const [activeSection, setActiveSection] = useState<AppSection>("dashboard");
  const [darkMode, setDarkMode] = useState<boolean>(() => localStorage.getItem("mindora.theme") !== "light");

  const canUseBranch = useMemo(() => selectedBranch.length > 0, [selectedBranch]);
  const completedSimulations = useMemo(
    () => simulationHistory.filter((x) => x.score_percent !== null && x.score_percent !== undefined),
    [simulationHistory]
  );
  const avgSimulationScore = useMemo(() => {
    if (completedSimulations.length === 0) return 0;
    const sum = completedSimulations.reduce((acc, x) => acc + Number(x.score_percent ?? 0), 0);
    return Math.round((sum / completedSimulations.length) * 100) / 100;
  }, [completedSimulations]);

  const examTopK = useMemo(() => {
    if (examQualityMode === "maximo") return 12;
    if (examQualityMode === "equilibrado") return 8;
    return 6;
  }, [examQualityMode]);

  const isDashboard = activeSection === "dashboard";
  const isTemarios = activeSection === "temarios";
  const isEstudiar = activeSection === "estudiar";
  const isExamenes = activeSection === "examenes";
  const isProgreso = activeSection === "progreso";
  const isConfig = activeSection === "config";

  // ── Backend health polling ─────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    let dotCount = 0;
    const dotTimer = setInterval(() => {
      dotCount = (dotCount + 1) % 4;
      setBackendLoadingDots(".".repeat(dotCount));
    }, 500);

    async function poll() {
      let attempts = 0;
      const maxAttempts = 50;
      while (!cancelled && attempts < maxAttempts) {
        attempts++;
        try {
          const ok = await checkHealth();
          if (ok && !cancelled) {
            setBackendReady(true);
            clearInterval(dotTimer);
            try {
              const setup = await getSetupStatus();
              setModelFound(setup.model_found);
              setModelExpectedDir(setup.expected_dir);
            } catch (err) {
              console.warn("Setup status check failed:", err);
              setModelFound(false);
            }
            try {
              await loadBranches();
            } catch (err) {
              console.warn("Loading branches failed:", err);
            }
            return;
          }
        } catch (err) {
          console.warn(`Health check attempt ${attempts} failed:`, err);
        }
        await new Promise((r) => setTimeout(r, 1200));
      }
      if (!cancelled) {
        clearInterval(dotTimer);
        setBackendReady(false);
        console.error("Backend failed to respond after max attempts");
      }
    }
    void poll();
    return () => {
      cancelled = true;
      clearInterval(dotTimer);
    };
  }, []);
  // ──────────────────────────────────────────────────────────────────────

  useEffect(() => {
    if (!simulationExpiresAt || !simulationId) return;
    const interval = setInterval(() => {
      const expires = new Date(simulationExpiresAt).getTime();
      const now = Date.now();
      const left = Math.floor((expires - now) / 1000);
      setSimulationTimeLeft(Math.max(0, left));
    }, 1000);
    return () => clearInterval(interval);
  }, [simulationExpiresAt, simulationId]);

  useEffect(() => {
    if (!simulationId || simulationTimeLeft > 0 || simulationResult || isAutoSubmittingSimulation) return;
    void handleSubmitSimulation(true);
  }, [simulationId, simulationTimeLeft, simulationResult, isAutoSubmittingSimulation]);

  useEffect(() => {
    const timer = setTimeout(() => setShowSplash(false), 5000);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setShowInfoModal(false);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    document.body.classList.toggle("light-mode", !darkMode);
    localStorage.setItem("mindora.theme", darkMode ? "dark" : "light");
  }, [darkMode]);

  function showToast(msg: string, type: "ok" | "err" = "ok") {
    setToast({ msg, type });
    setStatus(msg);
    setTimeout(() => setToast(null), 3500);
  }

  function getErrorMessage(err: unknown, fallback: string): string {
    if (err instanceof Error && err.message.trim().length > 0) return err.message;
    return fallback;
  }

  async function loadBranches() {
    try {
      const data = await fetchBranches();
      if (Array.isArray(data)) {
        setBranches(data);
        if (data.length > 0 && !selectedBranch) {
          setSelectedBranch(data[0].name);
        }
      }
    } catch (err) {
      console.error("Failed to load branches:", err);
      showToast(getErrorMessage(err, "No se pudo cargar ramas. Asegura que el core esté activo."), "err");
      setBranches([]);
    }
  }

  async function handleRefresh() {
    await loadBranches();
    if (!selectedBranch) {
      showToast("✅ Datos actualizados");
      return;
    }
    await Promise.all([
      loadDocuments(selectedBranch),
      loadSimulationHistory(selectedBranch),
      loadDailyRecs(selectedBranch)
    ]);
    showToast("✅ Datos actualizados");
  }

  useEffect(() => {
    if (selectedBranch) {
      loadDocuments(selectedBranch);
      loadSimulationHistory(selectedBranch);
      loadDailyRecs(selectedBranch);
    }
  }, [selectedBranch]);

  async function loadDocuments(branch: string) {
    try {
      const data = await listDocuments(branch);
      setDocuments(data.documents);
    } catch {
      setDocuments([]);
    }
  }

  async function loadSimulationHistory(branch: string) {
    try {
      const data = await getSimulationHistory(branch, 30);
      setSimulationHistory(data.items);
    } catch {
      setSimulationHistory([]);
    }
  }

  async function loadDailyRecs(branch: string) {
    try {
      const data = await getDailyRecommendations(branch);
      setDailyRecs(data.recommendations);
      setDailyRecsMsg(data.message);
    } catch {
      setDailyRecs([]);
      setDailyRecsMsg("");
    }
  }

  async function loadDictionary() {
    try {
      const data = await listCustomDictionary();
      setDictEntries(data.entries);
    } catch {
      setDictEntries([]);
    }
  }

  async function handleRemoveDictEntry(phrase: string) {
    try {
      await removeDictionaryPhrase(phrase);
      setDictEntries((prev) => prev.filter((e) => e.phrase !== phrase));
      setStatus(`Frase eliminada: "${phrase}"`);
    } catch (err) {
      showToast(getErrorMessage(err, "Error eliminando frase"), "err");
    }
  }

  async function handleCreateBranch() {
    setBranchNameError("");
    const name = branchName.trim();
    if (!name) {
      setBranchNameError("El nombre de la rama no puede estar vacío.");
      return;
    }
    if (name.length < 2) {
      setBranchNameError("Mínimo 2 caracteres.");
      return;
    }
    if (/[<>:"|?*\\]/.test(name)) {
      setBranchNameError("El nombre contiene caracteres no permitidos.");
      return;
    }
    try {
      const created = await createBranch(name);
      setBranches((prev: Branch[]) => [...prev, created]);
      setSelectedBranch(created.name);
      setBranchName("");
      showToast("✅ Rama creada");
    } catch (err) {
      setBranchNameError(getErrorMessage(err, "No se pudo crear la rama."));
    }
  }

  async function handleDeleteBranch() {
    if (!selectedBranch) return;
    const confirmed = window.confirm(`¿Seguro que quieres eliminar la rama "${selectedBranch}"? Esta acción no se puede deshacer.`);
    if (!confirmed) return;

    const branchToDelete = selectedBranch;
    try {
      await deleteBranch(branchToDelete);
      setBranches((prev) => {
        const updated = prev.filter((b) => b.name !== branchToDelete);
        setSelectedBranch(updated[0]?.name ?? "");
        return updated;
      });
      setDocuments([]);
      showToast("✅ Rama eliminada");
    } catch (err) {
      showToast(getErrorMessage(err, "Error al eliminar la rama"), "err");
    }
  }

  async function handleIngest() {
    setFileError("");
    if (!canUseBranch) {
      setFileError("Selecciona una rama primero.");
      return;
    }
    if (!file) {
      setFileError("Selecciona un archivo para subir.");
      return;
    }
    const allowed = [".pdf", ".docx", ".pptx", ".txt", ".png", ".jpg", ".jpeg"];
    const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    if (!allowed.includes(ext)) {
      setFileError(`Formato no soportado (${ext}). Usa PDF, DOCX, PPTX, TXT o imagen.`);
      return;
    }
    try {
      setIsUploading(true);
      setUploadProgress(0);
      const result = await ingestDocument(selectedBranch, file, (percent) => setUploadProgress(percent));
      showToast(`✅ Documento subido: ${file.name} (${result.chunks} fragmentos)`);
      await loadDocuments(selectedBranch);
      setFile(null);
      setTimeout(() => {
        setIsUploading(false);
        setUploadProgress(0);
      }, 1000);
    } catch (err) {
      setIsUploading(false);
      setUploadProgress(0);
      setFileError(getErrorMessage(err, "Error al subir el documento. Comprueba que el formato es compatible."));
    }
  }

  async function handleQuery() {
    setQuestionError("");
    if (!canUseBranch) { setQuestionError("Selecciona una rama primero."); return; }
    if (!question.trim()) { setQuestionError("Escribe una pregunta antes de buscar contexto."); return; }
    try {
      const result = await queryRag(
        selectedBranch,
        question,
        retrievalDepth,
        selectedStudyDocumentId === "all" ? undefined : selectedStudyDocumentId,
      );
      setChunks(result.results.map((r) => r.text));
      setStatus(`Resultados: ${result.results.length}`);
    } catch {
      showToast("Error al buscar contexto", "err");
    }
  }

  async function handleAsk() {
    setQuestionError("");
    if (!canUseBranch) { setQuestionError("Selecciona una rama primero."); return; }
    if (!question.trim()) { setQuestionError("Escribe una pregunta para continuar."); return; }
    if (question.trim().length < 3) { setQuestionError("La pregunta debe tener al menos 3 caracteres."); return; }
    try {
      const result = await askRag(
        selectedBranch,
        question,
        retrievalDepth,
        responseStyle,
        sessionId,
        selectedStudyDocumentId === "all" ? undefined : selectedStudyDocumentId,
      );
      setAnswer(result.answer);
      setContexts(result.contexts);
      setSources(result.sources ?? []);
      setLastAnswerStyle(responseStyle);
      setLastQuestion(question);
      if (result.session_id) {
        setSessionId(result.session_id);
      }
      setStatus("Respuesta generada");
    } catch (err) {
      const detail = err instanceof Error ? err.message : "No se pudo procesar la pregunta";
      setAnswer(
        "No he entendido o no he podido procesar esa pregunta en este momento.\n\n"
        + "Prueba así:\n"
        + "- 'Explícamelo fácil en 5 puntos'\n"
        + "- 'Resúmelo como si fuera para examen'\n"
        + "- '¿Cuáles son las ideas clave de este tema?'"
      );
      setContexts([]);
      setSources([]);
      showToast(`Error: ${detail}`, "err");
    }
  }

  function handleQuickExplain(mode: "facil" | "examen" | "ejemplos" | "pasos" | "minuto") {
    if (!question.trim()) return;
    if (mode === "facil") {
      setQuestion(`Explícamelo fácil: ${question}`);
      setResponseStyle("pasos");
      return;
    }
    if (mode === "examen") {
      setQuestion(`Explícamelo como si fuera examen: ${question}`);
      setResponseStyle("examen");
      return;
    }
    if (mode === "ejemplos") {
      setQuestion(`Explícamelo con ejemplos: ${question}`);
      setResponseStyle("detallada");
      return;
    }
    if (mode === "pasos") {
      setQuestion(`Explícamelo paso a paso: ${question}`);
      setResponseStyle("pasos");
      return;
    }
    setQuestion(`Explícamelo en 1 minuto: ${question}`);
    setResponseStyle("corta");
  }

  async function handleGenerateStudyPack() {
    if (!examTopic || !canUseBranch) return;
    try {
      const result = await generateStudyPack(selectedBranch, examTopic, Math.min(12, retrievalDepth + 2));
      setStudySummaryShort(result.summary_short);
      setStudySummaryLong(result.summary_long);
      setStudyIdeas(result.key_ideas);
      setStudyConcepts(result.concepts_to_memorize);
      setStudyExamQuestions(result.possible_exam_questions);
      setStudyMistakes(result.common_mistakes);
      setStudyMiniTest(result.mini_test);
      setStudySources(result.sources);
      setStatus("Pack de estudio generado");
    } catch {
      setStatus("Error generando pack de estudio");
    }
  }

  async function handleStartSimulation() {
    if (!canUseBranch || !examId) return;
    try {
      const sim = await startExamSimulation(selectedBranch, examId, simulationDuration);
      setSimulationId(sim.simulation_id);
      setSimulationQuestions(sim.questions);
      setSimulationAnswers({});
      setSimulationExpiresAt(sim.expires_at);
      setSimulationResult(null);
      setSimulationTimeLeft(sim.duration_minutes * 60);
      setIsAutoSubmittingSimulation(false);
      setStatus("Simulacro iniciado");
    } catch {
      setStatus("Error iniciando simulacro");
    }
  }

  function handleSimulationAnswerChange(number: number, answer: string) {
    setSimulationAnswers((prev) => ({ ...prev, [number]: answer }));
  }

  async function handleSubmitSimulation(isAuto = false) {
    if (!canUseBranch || !simulationId) return;
    if (isAuto) setIsAutoSubmittingSimulation(true);
    try {
      const payload = Object.entries(simulationAnswers).map(([number, answer]) => ({
        number: Number(number),
        answer: String(answer)
      }));
      const result = await submitExamSimulation(selectedBranch, simulationId, payload);
      setSimulationResult(result);
      setStatus(
        isAuto
          ? `Tiempo agotado. Simulacro entregado automáticamente. Nota: ${result.score_percent}%`
          : `Simulacro entregado. Nota: ${result.score_percent}%`
      );
      await loadSimulationHistory(selectedBranch);
    } catch {
      setStatus("Error entregando simulacro");
    } finally {
      if (isAuto) setIsAutoSubmittingSimulation(false);
    }
  }

  async function handleLearnPhrase() {
    setLearnPhraseError("");
    const phrase = learnPhraseText.trim();
    if (!phrase) {
      setLearnPhraseError("Escribe una frase para enseñarle a la IA.");
      return;
    }
    if (phrase.length < 4) {
      setLearnPhraseError("La frase debe tener al menos 4 caracteres.");
      return;
    }
    try {
      await learnPhrase({ phrase, intent: "general", response_style: responseStyle });
      setLearnPhraseText("");
      showToast("✅ Frase aprendida en el diccionario");
    } catch {
      setLearnPhraseError("Error al guardar la frase. Inténtalo de nuevo.");
    }
  }

  async function handleFeedback(useful: boolean) {
    if (!lastQuestion || !lastAnswerStyle) return;
    try {
      const res = await sendFeedback({
        question: lastQuestion,
        response_style: lastAnswerStyle,
        useful,
        answer_text: answer,
        branch: selectedBranch
      });
      if (res.status === "ignored") {
        setStatus("Feedback ignorado: usa estilo distinto de Auto para aprendizaje directo");
      } else {
        setStatus(useful ? "Gracias, la IA aprendió esta preferencia" : "Preferencia retirada");
      }
    } catch {
      setStatus("Error enviando feedback");
    }
  }

  async function handleExam() {
    setExamTopicError("");
    if (!canUseBranch) { setExamTopicError("Selecciona una rama con documentos subidos."); return; }
    if (!examTopic.trim()) {
      setExamTopicError("Escribe el tema del examen.");
      return;
    }
    if (examTopic.trim().length < 3) {
      setExamTopicError("El tema debe tener al menos 3 caracteres.");
      return;
    }
    if (examCount < 1 || examCount > 50) {
      setExamTopicError("El número de preguntas debe estar entre 1 y 50.");
      return;
    }
    try {
      const result = await generateExam(selectedBranch, examTopic, examCount, examDifficulty, examTopK, examType);
      setExamId(result.exam_id);
      setExamContent(result.exam_content);
      setAnswerKeyContent(result.answer_key_content);
      setExamAvgConfidence(result.avg_confidence ?? null);
      setExamWarnings(result.distractor_warnings ?? []);
      showToast("✅ Examen generado correctamente");
    } catch {
      setExamTopicError("Error al generar el examen. Asegúrate de tener documentos en la rama.");
    }
  }

  async function handleExportPdf() {
    if (!examId || !canUseBranch) return;
    try {
      const result = await exportExamPdf(selectedBranch, examId, "exam");
      setStatus(`PDF exportado: ${result.path}`);
    } catch {
      setStatus("Error exportando PDF");
    }
  }

  async function handleExportAnswerKeyPdf() {
    if (!examId || !canUseBranch) return;
    try {
      const result = await exportExamPdf(selectedBranch, examId, "answer_key");
      setStatus(`PDF solucionario exportado: ${result.path}`);
    } catch {
      setStatus("Error exportando PDF solucionario");
    }
  }

  async function handleExportDocx() {
    if (!examId || !canUseBranch) return;
    try {
      const result = await exportExamDocx(selectedBranch, examId, "exam");
      setStatus(`DOCX exportado: ${result.path}`);
    } catch {
      setStatus("Error exportando DOCX");
    }
  }

  async function handleExportAnswerKeyDocx() {
    if (!examId || !canUseBranch) return;
    try {
      const result = await exportExamDocx(selectedBranch, examId, "answer_key");
      setStatus(`DOCX solucionario exportado: ${result.path}`);
    } catch {
      setStatus("Error exportando DOCX solucionario");
    }
  }

  async function handleSolveUploadedExam() {
    if (!canUseBranch || !examSolveFile) return;
    try {
      const result = await solveUploadedExam(selectedBranch, examSolveFile, 8);
      setSolvedExamContent(result.solutions);
      setSolvedExamConfidence(result.avg_solution_confidence ?? null);
      setStatus("Examen subido y resuelto");
    } catch {
      setStatus("Error resolviendo examen subido");
    }
  }

  if (showSplash) {
    return (
      <div className="splash">
        <img src="/logo-byendika.png" alt="Logo by Endika" className="splash-logo" />
        <div className="splash-title">ENDIKA PRADERA</div>
        <div className="splash-subtitle">MINDORA</div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <aside className="left-sidebar">
        <div className="sidebar-brand">
          <img src="/logo-app.png" alt="MINDORA app icon" className="sidebar-logo" />
          <div>
            <h2>MINDORA</h2>
            <p>Tu tutor IA offline</p>
          </div>
        </div>

        <nav className="sidebar-nav">
          <button className={activeSection === "dashboard" ? "sidebar-link active" : "sidebar-link"} onClick={() => setActiveSection("dashboard")}>🏠 Dashboard</button>
          <button className={activeSection === "temarios" ? "sidebar-link active" : "sidebar-link"} onClick={() => setActiveSection("temarios")}>📚 Temarios</button>
          <button className={activeSection === "estudiar" ? "sidebar-link active" : "sidebar-link"} onClick={() => setActiveSection("estudiar")}>💬 Estudiar</button>
          <button className={activeSection === "examenes" ? "sidebar-link active" : "sidebar-link"} onClick={() => setActiveSection("examenes")}>📝 Exámenes</button>
          <button className={activeSection === "progreso" ? "sidebar-link active" : "sidebar-link"} onClick={() => setActiveSection("progreso")}>📈 Progreso</button>
          <button className={activeSection === "config" ? "sidebar-link active" : "sidebar-link"} onClick={() => setActiveSection("config")}>⚙️ Configuración</button>
        </nav>

        <div className="sidebar-tip">
          Flujo recomendado: Temarios → Estudiar → Exámenes → Progreso.
        </div>

        <div className="sidebar-footer-credit">Developed by ENDIKA PRADERA</div>
      </aside>

      <div className="container">
      <button
        className="info-fab"
        onClick={() => setShowInfoModal(true)}
        aria-label="Abrir información de la aplicación"
        title="Información detallada"
      >
        <img src="/logo-app.png" alt="Icono app" className="info-fab-icon" />
        Información
      </button>

      <button
        className="theme-fab"
        onClick={() => setDarkMode((v) => !v)}
        aria-label="Cambiar modo oscuro"
        title="Modo oscuro on/off"
      >
        {darkMode ? "🌙 Oscuro" : "☀️ Claro"}
      </button>

      {showInfoModal && (
        <div className="modal-overlay" onClick={() => setShowInfoModal(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setShowInfoModal(false)} aria-label="Cerrar modal">
              ✕
            </button>

            <img src="/logo-app.png" alt="MINDORA app icon" className="modal-logo" />
            <h2>Guía detallada de MINDORA</h2>

            <div className="modal-content">
              <h3>1) Gestión por ramas</h3>
              <p>
                Cada rama funciona como un espacio de estudio independiente. Puedes crear una rama por asignatura,
                por unidad o por alumno. Todo queda separado: documentos, exámenes, simulacros e historial.
              </p>

              <h3>2) Ingesta inteligente de documentos</h3>
              <p>
                MINDORA acepta PDF, DOCX, PPTX e imágenes. En imágenes aplica OCR para leer texto escaneado.
                Después divide el contenido en fragmentos semánticos (chunks), genera embeddings y los indexa en FAISS
                para búsquedas rápidas y precisas incluso con muchos apuntes.
              </p>

              <h3>3) Preguntas con RAG y fuentes</h3>
              <p>
                En “Pregunta (RAG)”, primero recupera contexto relevante desde tus documentos y luego genera la respuesta.
                Siempre muestra las fuentes usadas (archivo + chunk) para que puedas verificar de dónde salió cada idea.
                También puedes ver manualmente el contexto bruto con “Ver contexto”.
              </p>

              <h3>4) Estilos de respuesta y aprendizaje de preferencias</h3>
              <p>
                Puedes forzar estilo corto, detallado, por pasos o automático. Además, con “Aprender frase” y feedback
                útil/no útil, el sistema ajusta su diccionario de intenciones para responder mejor a tu forma de pedir.
              </p>

              <h3>5) Pack de estudio automático</h3>
              <p>
                Desde un tema genera: resumen corto, resumen largo, ideas clave, conceptos para memorizar, preguntas
                posibles de examen, errores típicos, mini test y fuentes. Es ideal para preparar repasos rápidos y
                sesiones de estudio estructuradas sin salir de la app.
              </p>

              <h3>6) Generador de exámenes académico</h3>
              <p>
                Permite crear exámenes mixtos o por tipo (test simple, múltiple, desarrollo), con dificultad y número
                de preguntas configurables. También exporta examen y solucionario por separado en PDF y DOCX.
              </p>

              <h3>7) Simulacro real con tiempo</h3>
              <p>
                Ejecuta simulacros cronometrados con entrega manual o automática al agotarse el tiempo. Corrige test de
                forma exacta y desarrollo con evaluación asistida por IA, calculando nota final y temas débiles.
              </p>

              <h3>8) Historial y analítica de progreso</h3>
              <p>
                Guarda simulacros anteriores, media de nota, número de intentos y recomendaciones diarias en función de
                los temas donde más fallas. Esto facilita repetición espaciada y priorización de estudio.
              </p>

              <h3>9) Modo 100% offline y privacidad</h3>
              <p>
                Todo se ejecuta localmente en tu equipo: modelo LLM, embeddings, índice vectorial y base de datos.
                No envía tus apuntes a servidores externos. Es apto para uso educativo con datos sensibles.
              </p>

              <h3>10) Flujo recomendado de uso</h3>
              <p>
                1) Crea rama → 2) Sube apuntes → 3) Pregunta y genera pack → 4) Crea examen → 5) Haz simulacro
                → 6) Revisa temas débiles → 7) Repite hasta dominar el temario.
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="header">
      {/* header content starts here */}
        <div>
          <h1>MINDORA</h1>
          <span className="badge">MINDORA</span>
        </div>
      </div>

      {/* ── Backend loading screen ──────────────────────────────────────── */}
      {!backendReady && (
        <div className="splash-overlay">
          <div className="splash-card">
            <h1>MINDORA</h1>
            <p style={{ fontSize: "1.1rem", marginBottom: 8 }}>
              Iniciando la IA{backendLoadingDots}
            </p>
            <p style={{ fontSize: "0.85rem", color: "#888" }}>
              La primera vez puede tardar unos segundos mientras el motor de IA arranca.
            </p>
            <div className="loading-bar">
              <div className="loading-bar-inner" />
            </div>
          </div>
        </div>
      )}

      {/* ── Model not found screen ──────────────────────────────────────── */}
      {backendReady && modelFound === false && (
        <div className="splash-overlay">
          <div className="splash-card">
            <h1>⚠️ Modelo no encontrado</h1>
            <p style={{ marginBottom: 12 }}>
              Para usar MINDORA necesitas el archivo del modelo de IA (formato <strong>.gguf</strong>).
            </p>
            <div className="result" style={{ textAlign: "left", marginBottom: 16 }}>
              <p><strong>1.</strong> Descarga el modelo (ej: <em>mistral-7b-instruct-v0.2.Q4_K_M.gguf</em>)</p>
              <p><strong>2.</strong> Colócalo en esta carpeta:</p>
              <code style={{ display: "block", background: "#f1f5f9", padding: "8px 12px", borderRadius: 6, fontSize: "0.85rem", wordBreak: "break-all", margin: "8px 0" }}>
                {modelExpectedDir}
              </code>
              <p><strong>3.</strong> Crea la carpeta si no existe, copia el archivo .gguf ahí y pulsa el botón.</p>
            </div>
            <button
              style={{ width: "100%", padding: "12px 0", fontSize: "1rem" }}
              onClick={async () => {
                try {
                  const setup = await getSetupStatus();
                  setModelFound(setup.model_found);
                } catch { /* keep waiting */ }
              }}
            >
              ✅ Ya lo tengo — Comprobar de nuevo
            </button>
          </div>
        </div>
      )}

      {/* ── Main UI (shown only when backend ready & model found) ────────── */}
      {backendReady && modelFound !== false && <div className="header-bottom">
        <div className="row top-toolbar-row">
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

          <select
            value={activeSection}
            onChange={(e: ChangeEvent<HTMLSelectElement>) => setActiveSection(e.target.value as AppSection)}
            title="Ir a sección"
          >
            <option value="dashboard">Dashboard</option>
            <option value="temarios">Temarios</option>
            <option value="estudiar">Estudiar</option>
            <option value="examenes">Exámenes</option>
            <option value="progreso">Progreso</option>
            <option value="config">Configuración</option>
          </select>

          <select
            value={retrievalDepth}
            onChange={(e: ChangeEvent<HTMLSelectElement>) => setRetrievalDepth(Number(e.target.value))}
            title="Profundidad de recuperación"
          >
            <option value={4}>Búsqueda rápida (4)</option>
            <option value={6}>Búsqueda equilibrada (6)</option>
            <option value={8}>Búsqueda profunda (8)</option>
            <option value={10}>Búsqueda máxima (10)</option>
          </select>

          <button onClick={() => void handleRefresh()}>Refrescar</button>
        </div>
      </div>}

      <div className="card section-title-card">
        <h3>
          {isDashboard && "Dashboard"}
          {isTemarios && "Temarios"}
          {isEstudiar && "Estudiar"}
          {isExamenes && "Exámenes"}
          {isProgreso && "Progreso"}
          {isConfig && "Configuración"}
        </h3>
        <p>
          {isDashboard && "Resumen general y accesos rápidos."}
          {isTemarios && "Gestiona tus documentos y estructura del contenido."}
          {isEstudiar && "Consulta el material con IA y crea explicaciones guiadas."}
          {isExamenes && "Genera, exporta y practica evaluaciones."}
          {isProgreso && "Analiza tu evolución y detecta puntos débiles."}
          {isConfig && "Ajustes y preferencias avanzadas."}
        </p>
      </div>

      {isDashboard && (
        <div className="grid">
          <div className="card">
            <h3>Resumen rápido</h3>
            <div className="row" style={{ marginBottom: 10 }}>
              <span className="badge">Rama: {selectedBranch || "Sin seleccionar"}</span>
              <span className="badge">Documentos: {documents.length}</span>
              <span className="badge">Simulacros: {simulationHistory.length}</span>
            </div>
            <p>Media actual: <strong>{avgSimulationScore}%</strong></p>
          </div>

          <div className="card">
            <h3>Acciones rápidas</h3>
            <div className="row">
              <button onClick={() => setActiveSection("estudiar")}>Continuar estudiando</button>
              <button onClick={() => setActiveSection("examenes")}>Generar examen</button>
              <button onClick={() => setActiveSection("temarios")}>Gestionar temarios</button>
              <button onClick={() => setActiveSection("progreso")}>Ver progreso</button>
            </div>
          </div>
        </div>
      )}

      <div className="grid">
        {isTemarios && <div className="card">
          <h3>Crear rama</h3>
          <input
            placeholder="Nombre de la rama"
            value={branchName}
            onChange={(e: ChangeEvent<HTMLInputElement>) => { setBranchName(e.target.value); setBranchNameError(""); }}
            className={branchNameError ? "input-error" : ""}
          />
          {branchNameError && <span className="field-error">{branchNameError}</span>}
          <div className="row">
            <button onClick={handleCreateBranch}>Crear</button>
            <button onClick={handleDeleteBranch} disabled={!canUseBranch}>
              Eliminar
            </button>
          </div>
        </div>}

        {isTemarios && <div className="card">
          <h3>Ingesta de documentos</h3>
          {!canUseBranch && <span className="field-error">Selecciona una rama antes de subir documentos.</span>}
          <div className="upload-form-group">
            <input
              type="file"
              className={fileError ? "input-error" : ""}
              onChange={(e: ChangeEvent<HTMLInputElement>) => { setFile(e.target.files?.[0] ?? null); setFileError(""); }}
              disabled={isUploading}
            />
            <button onClick={handleIngest} disabled={!canUseBranch || isUploading}>
              {isUploading ? "Subiendo..." : "Subir"}
            </button>
          </div>
          {isUploading && (
            <div className="upload-progress">
              <div className="progress-bar-container">
                <div className="progress-bar-fill" style={{ width: `${uploadProgress}%` }}></div>
              </div>
              <span className="progress-text">{Math.round(uploadProgress)}%</span>
            </div>
          )}
          {fileError && <span className="field-error">{fileError}</span>}
          {documents.length > 0 && (
            <div className="result" style={{ marginTop: 12 }}>
              <strong>Documentos:</strong>
              <ul>
                {documents.map((doc) => (
                  <li key={doc.id}>{doc.filename}</li>
                ))}
              </ul>
            </div>
          )}
        </div>}

        {isEstudiar && <div className="card">
          <h3>Pregunta (RAG)</h3>
          <select
            value={selectedStudyDocumentId}
            onChange={(e: ChangeEvent<HTMLSelectElement>) => {
              const v = e.target.value;
              setSelectedStudyDocumentId(v === "all" ? "all" : Number(v));
            }}
          >
            <option value="all">Todo el temario</option>
            {documents.map((doc) => (
              <option key={doc.id} value={doc.id}>{doc.filename}</option>
            ))}
          </select>
          <textarea
            rows={4}
            placeholder="Escribe tu pregunta"
            value={question}
            className={questionError ? "input-error" : ""}
            onChange={(e: ChangeEvent<HTMLTextAreaElement>) => { setQuestion(e.target.value); setQuestionError(""); }}
          />
          {questionError && <span className="field-error">{questionError}</span>}
          <select
            value={responseStyle}
            onChange={(e: ChangeEvent<HTMLSelectElement>) => setResponseStyle(e.target.value as ResponseStyle)}
          >
            <option value="auto">Auto (por texto)</option>
            <option value="corta">Corta</option>
            <option value="detallada">Detallada</option>
            <option value="pasos">Explicativa por pasos</option>
            <option value="detallada_pasos">Detallada por pasos</option>
            <option value="examen">Modo examen</option>
            <option value="profesor">Modo profesor</option>
            <option value="companero">Modo compañero</option>
          </select>
          <div className="row">
            <button onClick={handleQuery} disabled={!canUseBranch}>
              Ver contexto
            </button>
            <button onClick={handleAsk} disabled={!canUseBranch}>
              Responder
            </button>
          </div>
          <div className="row" style={{ marginTop: 10 }}>
            <select
              value={quickAction}
              onChange={(e: ChangeEvent<HTMLSelectElement>) => setQuickAction(e.target.value as "facil" | "examen" | "ejemplos" | "pasos" | "minuto")}
            >
              <option value="facil">Explícamelo fácil</option>
              <option value="examen">Como examen</option>
              <option value="ejemplos">Con ejemplos</option>
              <option value="pasos">Paso a paso</option>
              <option value="minuto">En 1 minuto</option>
            </select>
            <button onClick={() => handleQuickExplain(quickAction)}>Aplicar modo rápido</button>
            <button onClick={() => setResponseStyle("profesor")}>Modo profesor</button>
            <button onClick={() => setResponseStyle("companero")}>Modo compañero</button>
          </div>
          <div className="row" style={{ marginTop: 10 }}>
            <input
              placeholder="Enseña una frase (ej: 'hazlo super corto')"
              value={learnPhraseText}
              className={learnPhraseError ? "input-error" : ""}
              onChange={(e: ChangeEvent<HTMLInputElement>) => { setLearnPhraseText(e.target.value); setLearnPhraseError(""); }}
            />
            <button onClick={handleLearnPhrase}>Aprender frase</button>
          </div>
          {learnPhraseError && <span className="field-error" style={{ marginTop: 4 }}>{learnPhraseError}</span>}
        </div>}

        {isExamenes && <div className="card">
          <h3>Generar examen</h3>
          <input
            placeholder="Tema del examen"
            value={examTopic}
            className={examTopicError ? "input-error" : ""}
            onChange={(e: ChangeEvent<HTMLInputElement>) => { setExamTopic(e.target.value); setExamTopicError(""); }}
          />
          {examTopicError && <span className="field-error">{examTopicError}</span>}

          <details className="menu-panel" open>
            <summary>⚙️ Configuración del examen</summary>
            <div className="menu-panel-body">
              <div className="form-grid-4">
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={examCount}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => setExamCount(Number(e.target.value))}
                  title="Número de preguntas"
                />
                <select
                  value={examDifficulty}
                  onChange={(e: ChangeEvent<HTMLSelectElement>) => setExamDifficulty(e.target.value)}
                  title="Dificultad"
                >
                  <option value="baja">Dificultad baja</option>
                  <option value="media">Dificultad media</option>
                  <option value="alta">Dificultad alta</option>
                </select>
                <select
                  value={examType}
                  onChange={(e: ChangeEvent<HTMLSelectElement>) => setExamType(e.target.value as ExamType)}
                  title="Tipo de examen"
                >
                  <option value="mixto">Tipo mixto</option>
                  <option value="test_simple">Test simple</option>
                  <option value="test_multiple">Test múltiple</option>
                  <option value="desarrollo">Desarrollo</option>
                </select>
                <select
                  value={examQualityMode}
                  onChange={(e: ChangeEvent<HTMLSelectElement>) => setExamQualityMode(e.target.value as "rapido" | "equilibrado" | "maximo")}
                  title="Modo de calidad"
                >
                  <option value="rapido">Modo rápido (top_k 6)</option>
                  <option value="equilibrado">Modo equilibrado (top_k 8)</option>
                  <option value="maximo">Modo máximo (top_k 12)</option>
                </select>
              </div>
              <div className="row action-row">
                <button onClick={handleExam} disabled={!canUseBranch}>
                  Generar examen
                </button>
                <button onClick={handleGenerateStudyPack} disabled={!canUseBranch || !examTopic}>
                  Generar pack de estudio
                </button>
              </div>
            </div>
          </details>

          <details className="menu-panel">
            <summary>📤 Exportación</summary>
            <div className="menu-panel-body">
              <div className="row action-row">
                <button onClick={handleExportPdf} disabled={!examId || !canUseBranch}>Exportar PDF examen</button>
                <button onClick={handleExportDocx} disabled={!examId || !canUseBranch}>Exportar DOCX examen</button>
                <button onClick={handleExportAnswerKeyPdf} disabled={!examId || !canUseBranch}>Exportar PDF solucionario</button>
                <button onClick={handleExportAnswerKeyDocx} disabled={!examId || !canUseBranch}>Exportar DOCX solucionario</button>
              </div>
            </div>
          </details>

          <details className="menu-panel">
            <summary>⏱️ Simulacro y resolución</summary>
            <div className="menu-panel-body">
              <div className="row action-row">
                <input
                  type="number"
                  min={5}
                  max={240}
                  value={simulationDuration}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => setSimulationDuration(Number(e.target.value))}
                />
                <button onClick={handleStartSimulation} disabled={!canUseBranch || !examId}>
                  Iniciar simulacro real
                </button>
              </div>
              <div className="row action-row">
                <input
                  type="file"
                  onChange={(e: ChangeEvent<HTMLInputElement>) => setExamSolveFile(e.target.files?.[0] ?? null)}
                />
                <button onClick={handleSolveUploadedExam} disabled={!examSolveFile || !canUseBranch}>
                  Subir y resolver examen
                </button>
              </div>
            </div>
          </details>

          {examAvgConfidence !== null && (
            <div className="result" style={{ marginTop: 10 }}>
              <strong>Calidad del examen:</strong> {Math.round(examAvgConfidence * 100)}%
              {examWarnings.length > 0 && (
                <>
                  <br />
                  <strong>Ajustes recomendados:</strong>
                  <ul>
                    {examWarnings.slice(0, 5).map((w, i) => <li key={`warn-${i}`}>{w}</li>)}
                  </ul>
                </>
              )}
            </div>
          )}
        </div>}
      </div>

      {/* Toast de notificación (reemplaza la tarjeta Estado) */}
      {toast && (
        <div className={`toast-notification toast-${toast.type}`}>
          {toast.msg}
        </div>
      )}

      {/* Daily Recommendations panel */}
      {canUseBranch && (isDashboard || isProgreso) && (
        <div className="card">
          <h3>📅 Recomendaciones de hoy</h3>
          <p style={{ fontSize: "0.85rem", color: "#666", marginBottom: 8 }}>{dailyRecsMsg || "Carga tus simulacros para ver recomendaciones."}</p>
          {dailyRecs.length > 0 ? (
            <ul>
              {dailyRecs.map((r, i) => (
                <li key={`rec-${i}`} style={{ marginBottom: 6 }}>
                  <strong>{r.topic}</strong>{" "}
                  <span className="badge" style={{ fontSize: "0.75rem" }}>
                    Fallado {r.fail_count}×
                  </span>
                  <br />
                  <span style={{ fontSize: "0.85rem", color: "#555" }}>{r.suggestion}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p style={{ fontSize: "0.85rem", color: "#888" }}>
              ¡Sin alertas! Sigue practicando simulacros para obtener recomendaciones personalizadas.
            </p>
          )}
          <button
            style={{ marginTop: 8 }}
            onClick={() => { if (selectedBranch) void loadDailyRecs(selectedBranch); }}
          >
            🔄 Actualizar recomendaciones
          </button>
        </div>
      )}

      {/* Dictionary CRUD panel */}
      {isConfig && <div className="card">
        <h3>📖 Diccionario de intenciones</h3>
        <div className="row" style={{ marginBottom: 8 }}>
          <button
            onClick={() => {
              setShowDictPanel((v) => !v);
              if (!showDictPanel) void loadDictionary();
            }}
          >
            {showDictPanel ? "Ocultar diccionario" : "Ver mis frases aprendidas"}
          </button>
        </div>
        {showDictPanel && (
          <>
            {dictEntries.length === 0 ? (
              <p style={{ fontSize: "0.85rem", color: "#888" }}>
                Aún no has añadido frases personalizadas. Usa "Aprender frase" para enseñarle nuevas frases a la IA.
              </p>
            ) : (
              <div className="result">
                <ul style={{ margin: 0, paddingLeft: 16 }}>
                  {dictEntries.map((e) => (
                    <li key={e.phrase} style={{ marginBottom: 6, display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                      <span style={{ fontWeight: 600 }}>{e.phrase}</span>
                      <span className="badge" style={{ fontSize: "0.73rem" }}>{e.intent}</span>
                      <span className="badge" style={{ fontSize: "0.73rem", background: "#d1fae5", color: "#065f46" }}>{e.response_style}</span>
                      <button
                        style={{ padding: "2px 10px", fontSize: "0.8rem", background: "#fee2e2", color: "#b91c1c", border: "1px solid #fca5a5" }}
                        onClick={() => void handleRemoveDictEntry(e.phrase)}
                      >
                        ✕ Eliminar
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </div>}

      {(isDashboard || isProgreso) && <div className="card">
        <h3>Progreso de simulacros</h3>
        <div className="row" style={{ marginBottom: 10 }}>
          <span className="badge">Simulacros: {simulationHistory.length}</span>
          <span className="badge">Completados: {completedSimulations.length}</span>
          <span className="badge">Media: {avgSimulationScore}%</span>
        </div>
        {simulationHistory.length > 0 ? (
          <div className="result">
            <ul>
              {simulationHistory.slice(0, 8).map((s) => (
                <li key={s.simulation_id}>
                  {s.topic} · {s.status} · nota {s.score_percent ?? "-"}%
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <p>Aún no hay simulacros guardados.</p>
        )}
      </div>}

      {isEstudiar && chunks.length > 0 && (
        <div className="card">
          <h3>Contextos</h3>
          {chunks.map((c, idx) => (
            <div key={idx} className="result">
              {c}
            </div>
          ))}
        </div>
      )}

      {isEstudiar && answer && (
        <div className="card">
          <h3>Respuesta</h3>
          {lastAnswerStyle && (
            <p className="badge" style={{ marginBottom: 10 }}>
              Estilo: {styleLabel(lastAnswerStyle)}
            </p>
          )}
          <div className="result">{answer}</div>
          {sources.length > 0 && (
            <div className="result" style={{ marginTop: 10 }}>
              <strong>Fuentes:</strong>
              <ul>
                {sources.map((s, i) => (
                  <li key={`${s}-${i}`}>{s}</li>
                ))}
              </ul>
            </div>
          )}
          <div className="row" style={{ marginTop: 10 }}>
            <button onClick={() => handleFeedback(true)}>👍 Útil</button>
            <button onClick={() => handleFeedback(false)}>👎 No útil</button>
          </div>
        </div>
      )}

      {isEstudiar && studySummaryShort && (
        <div className="card">
          <h3>Pack de estudio</h3>
          <div className="result">
            <strong>Resumen corto:</strong>
            <p>{studySummaryShort}</p>
            <strong>Resumen largo:</strong>
            <p>{studySummaryLong}</p>
            <strong>Ideas clave:</strong>
            <ul>{studyIdeas.map((x, i) => <li key={`idea-${i}`}>{x}</li>)}</ul>
            <strong>Conceptos para memorizar:</strong>
            <ul>{studyConcepts.map((x, i) => <li key={`concept-${i}`}>{x}</li>)}</ul>
            <strong>Posibles preguntas de examen:</strong>
            <ul>{studyExamQuestions.map((x, i) => <li key={`pq-${i}`}>{x}</li>)}</ul>
            <strong>Errores típicos:</strong>
            <ul>{studyMistakes.map((x, i) => <li key={`err-${i}`}>{x}</li>)}</ul>
            <strong>Mini test rápido:</strong>
            <ul>{studyMiniTest.map((x, i) => <li key={`mt-${i}`}>{x}</li>)}</ul>
            <strong>Fuentes:</strong>
            <ul>{studySources.map((x, i) => <li key={`src-${i}`}>{x}</li>)}</ul>
          </div>
        </div>
      )}

      {isExamenes && examContent && (
        <div className="card">
          <h3>Examen</h3>
          <div className="result">{examContent}</div>
        </div>
      )}

      {isExamenes && simulationId && simulationQuestions.length > 0 && (
        <div className="card">
          <h3>Simulacro real</h3>
          <p>
            Tiempo restante: <strong>{formatSeconds(simulationTimeLeft)}</strong>
          </p>
          {simulationTimeLeft === 0 && <p className="warning-text">Tiempo agotado. Entrega automática en curso…</p>}
          {simulationQuestions.map((q) => (
            <div key={q.number} className="result" style={{ marginBottom: 10 }}>
              <strong>
                {q.number}) [{q.type}] {q.statement}
              </strong>
              {q.options.length > 0 && (
                <ul>
                  {q.options.map((o, i) => (
                    <li key={`${q.number}-opt-${i}`}>{o}</li>
                  ))}
                </ul>
              )}
              <input
                placeholder="Tu respuesta"
                value={simulationAnswers[q.number] ?? ""}
                onChange={(e: ChangeEvent<HTMLInputElement>) => handleSimulationAnswerChange(q.number, e.target.value)}
              />
            </div>
          ))}
          <button onClick={() => handleSubmitSimulation(false)} disabled={isAutoSubmittingSimulation}>
            Entregar simulacro
          </button>
        </div>
      )}

      {isExamenes && simulationResult && (
        <div className="card">
          <h3>Resultado simulacro</h3>
          <div className="result">
            <p>
              Estado: <strong>{simulationResult.status}</strong>
            </p>
            <p>
              Aciertos: {simulationResult.correct_answers}/{simulationResult.total_questions}
            </p>
            <p>
              Nota: <strong>{simulationResult.score_percent}%</strong>
            </p>
            {simulationResult.weak_topics.length > 0 && (
              <>
                <strong>Temas donde has pinchado:</strong>
                <ul>
                  {simulationResult.weak_topics.map((w, i) => (
                    <li key={`weak-${i}`}>{w}</li>
                  ))}
                </ul>
              </>
            )}
            <strong>Análisis de errores:</strong>
            <ul>
              {simulationResult.results.map((r) => (
                <li key={`res-${r.number}`}>
                  {r.number}) {r.correct ? "✅" : "❌"} {r.feedback}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {isExamenes && answerKeyContent && (
        <div className="card">
          <h3>Solucionario</h3>
          <div className="result">{answerKeyContent}</div>
        </div>
      )}

      {isExamenes && solvedExamContent && (
        <div className="card">
          <h3>Resolución de examen subido</h3>
          {solvedExamConfidence !== null && (
            <p className="badge" style={{ marginBottom: 10 }}>
              Confianza media estimada: {Math.round(solvedExamConfidence * 100)}%
            </p>
          )}
          <div className="result">{solvedExamContent}</div>
        </div>
      )}

      {isEstudiar && contexts.length > 0 && (
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
    </div>
  );
}
