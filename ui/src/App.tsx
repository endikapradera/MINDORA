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

const DIMSEG_QUESTION_BANK: string[] = [
  "¿Qué es la seguridad de la información?",
  "¿Qué significa el concepto de riesgo en seguridad informática?",
  "¿Qué es un riesgo residual?",
  "¿Qué diferencia hay entre riesgo aceptable y riesgo inasumible?",
  "¿Qué es la ingeniería social?",
  "¿Qué es el phishing?",
  "¿Qué es el vishing?",
  "¿Qué es el shoulder surfing?",
  "¿Qué es el dumpster diving?",
  "¿Qué es un ataque de fuerza bruta?",
  "¿Qué es un ataque por diccionario?",
  "¿Qué es un ataque DoS?",
  "¿Qué es un ataque DDoS?",
  "¿Qué es un ataque Man in the Middle?",
  "¿Qué es el DNS poisoning?",
  "¿Qué es el spoofing?",
  "¿Qué es una SQL Injection?",
  "¿Qué es un ataque Zero-Day?",
  "¿Qué es el clickjacking?",
  "¿Qué diferencia hay entre codificar y cifrar?",
  "Explícame las principales estrategias para la gestión del riesgo en seguridad informática.",
  "Describe qué es la ingeniería social y cuáles son sus principales fases.",
  "Explica las diferencias entre codificación y cifrado.",
  "Describe los principales tipos de ataques a redes.",
  "Explica cómo funcionan los ataques de contraseñas.",
  "Analiza los ataques más comunes a aplicaciones web.",
  "Explica el concepto de riesgo residual y su importancia en la gestión de riesgos.",
  "Describe el proceso de explotación en un ataque de ingeniería social.",
  "Explica técnicas para prevenir ataques informáticos.",
  "Analiza la importancia de la gestión de riesgos en una organización.",
  "Analiza cómo una organización puede reducir el riesgo residual tras aplicar controles.",
  "Explica cómo se desarrolla un ataque de ingeniería social desde reconocimiento hasta explotación.",
  "Describe amenazas a una red corporativa y medidas de defensa.",
  "Explica cómo funcionan los ataques de denegación de servicio y su impacto.",
  "Analiza el papel de la ingeniería social en incidentes actuales.",
  "Explica cómo ataques a aplicaciones web comprometen datos organizacionales.",
  "Describe medidas para prevenir ataques de phishing.",
  "Analiza la importancia de la concienciación del usuario en seguridad.",
  "Explícame qué es el phishing como si fuera un estudiante de primero.",
  "Dame un ejemplo real de ataque de ingeniería social.",
  "¿Cómo puedo protegerme de ataques de fuerza bruta?",
  "¿Qué diferencia hay entre DoS y DDoS?",
  "¿Por qué el factor humano es el eslabón más débil de la seguridad?",
  "Explícame SQL Injection con un ejemplo sencillo.",
  "¿Cómo funciona un ataque Man in the Middle?",
  "¿Qué controles de seguridad pueden reducir el riesgo?",
  "Resume el PDF 1-RESUMEN DIMSEG en 5 puntos clave.",
  "Explícamelo fácil: quiero que me expliques el PDF 1-RESUMEN DIMSEG.",
];

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
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedStudyDocumentId, setSelectedStudyDocumentId] = useState<number | "all">("all");
  const [question, setQuestion] = useState("");
  const [responseStyle, setResponseStyle] = useState<ResponseStyle>("auto");
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
  const [examId, setExamId] = useState("");
  const [examContent, setExamContent] = useState("");
  const [answerKeyContent, setAnswerKeyContent] = useState("");
  const [examSolveFile, setExamSolveFile] = useState<File | null>(null);
  const [solvedExamContent, setSolvedExamContent] = useState("");
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
  const [dictEntries, setDictEntries] = useState<DictionaryEntry[]>([]);
  const [showDictPanel, setShowDictPanel] = useState(false);
  const [dailyRecs, setDailyRecs] = useState<DailyRecommendationItem[]>([]);
  const [dailyRecsMsg, setDailyRecsMsg] = useState("");
  const [activeSection, setActiveSection] = useState<AppSection>("dashboard");
  const [darkMode, setDarkMode] = useState<boolean>(() => localStorage.getItem("mindora.theme") !== "light");
  const [dimsegIdx, setDimsegIdx] = useState(0);

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
      while (!cancelled) {
        const ok = await checkHealth();
        if (ok && !cancelled) {
          setBackendReady(true);
          clearInterval(dotTimer);
          // Check if LLM model is found
          try {
            const setup = await getSetupStatus();
            setModelFound(setup.model_found);
            setModelExpectedDir(setup.expected_dir);
          } catch {
            setModelFound(false);
          }
          // Now load branches since backend is up
          await loadBranches();
          return;
        }
        await new Promise((r) => setTimeout(r, 1200));
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
    } catch {
      setStatus("Error eliminando frase");
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
      setStatus("Rama eliminada");
    } catch {
      setStatus("Error eliminando rama");
    }
  }

  async function handleIngest() {
    if (!file || !canUseBranch) return;
    try {
      const result = await ingestDocument(selectedBranch, file);
      setStatus(`Documento ingresado. Chunks: ${result.chunks}`);
      await loadDocuments(selectedBranch);
    } catch {
      setStatus("Error en ingesta");
    }
  }

  async function handleQuery() {
    if (!question || !canUseBranch) return;
    try {
      const result = await queryRag(
        selectedBranch,
        question,
        5,
        selectedStudyDocumentId === "all" ? undefined : selectedStudyDocumentId,
      );
      setChunks(result.results.map((r) => r.text));
      setStatus(`Resultados: ${result.results.length}`);
    } catch {
      setStatus("Error en query");
    }
  }

  async function handleAsk() {
    if (!question || !canUseBranch) return;
    try {
      const result = await askRag(
        selectedBranch,
        question,
        5,
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
        + "- 'Explícame fácil el PDF 1-RESUMEN DIMSENG'\n"
        + "- 'Resume el documento 1-RESUMEN DIMSENG en 5 puntos'\n"
        + "- '¿Cuáles son las ideas clave del PDF 1-RESUMEN DIMSENG?'"
      );
      setContexts([]);
      setSources([]);
      setStatus(`Error en ask: ${detail}`);
    }
  }

  function handleNewChat() {
    setSessionId(crypto.randomUUID());
    setAnswer("");
    setContexts([]);
    setChunks([]);
    setSources([]);
    setStatus("Nuevo chat iniciado");
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

  function handleLoadDimsegQuestion() {
    const q = DIMSEG_QUESTION_BANK[dimsegIdx % DIMSEG_QUESTION_BANK.length];
    setQuestion(q);
    setDimsegIdx((prev) => (prev + 1) % DIMSEG_QUESTION_BANK.length);
    setStatus("Pregunta de batería DIMSEG cargada");
  }

  async function handleGenerateStudyPack() {
    if (!examTopic || !canUseBranch) return;
    try {
      const result = await generateStudyPack(selectedBranch, examTopic, 6);
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
    const phrase = learnPhraseText.trim();
    if (!phrase) return;
    try {
      await learnPhrase({ phrase, intent: "general", response_style: responseStyle });
      setLearnPhraseText("");
      setStatus("Frase aprendida en diccionario");
    } catch {
      setStatus("Error guardando frase");
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
    if (!examTopic || !canUseBranch) return;
    try {
      const result = await generateExam(selectedBranch, examTopic, examCount, examDifficulty, 6, examType);
      setExamId(result.exam_id);
      setExamContent(result.exam_content);
      setAnswerKeyContent(result.answer_key_content);
      setStatus("Examen generado");
    } catch {
      setStatus("Error generando examen");
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
          <button onClick={handleNewChat}>Nuevo chat</button>
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
            onChange={(e: ChangeEvent<HTMLInputElement>) => setBranchName(e.target.value)}
          />
          <div className="row">
            <button onClick={handleCreateBranch}>Crear</button>
            <button onClick={handleDeleteBranch} disabled={!canUseBranch}>
              Eliminar
            </button>
          </div>
        </div>}

        {isTemarios && <div className="card">
          <h3>Ingesta de documentos</h3>
          <input
            type="file"
            onChange={(e: ChangeEvent<HTMLInputElement>) => setFile(e.target.files?.[0] ?? null)}
          />
          <button onClick={handleIngest} disabled={!file || !canUseBranch}>
            Ingestar
          </button>
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
          <div className="row" style={{ marginBottom: 10 }}>
            <button onClick={handleLoadDimsegQuestion}>Cargar pregunta DIMSEG</button>
            <span className="badge">Banco: {DIMSEG_QUESTION_BANK.length} preguntas</span>
          </div>
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
            onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setQuestion(e.target.value)}
          />
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
            <button onClick={() => handleQuickExplain("facil")}>Explícamelo fácil</button>
            <button onClick={() => handleQuickExplain("examen")}>Como examen</button>
          </div>
          <div className="row" style={{ marginTop: 8 }}>
            <button onClick={() => handleQuickExplain("ejemplos")}>Con ejemplos</button>
            <button onClick={() => handleQuickExplain("pasos")}>Paso a paso</button>
            <button onClick={() => handleQuickExplain("minuto")}>En 1 minuto</button>
            <button onClick={() => setResponseStyle("profesor")}>Modo profesor</button>
            <button onClick={() => setResponseStyle("companero")}>Modo compañero</button>
          </div>
          <div className="row" style={{ marginTop: 10 }}>
            <input
              placeholder="Enseña una frase (ej: 'hazlo super corto')"
              value={learnPhraseText}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setLearnPhraseText(e.target.value)}
            />
            <button onClick={handleLearnPhrase}>Aprender frase</button>
          </div>
        </div>}

        {isExamenes && <div className="card">
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
            <select
              value={examType}
              onChange={(e: ChangeEvent<HTMLSelectElement>) => setExamType(e.target.value as ExamType)}
            >
              <option value="mixto">Mixto</option>
              <option value="test_simple">Test simple</option>
              <option value="test_multiple">Test múltiple</option>
              <option value="desarrollo">Desarrollo</option>
            </select>
          </div>
          <button onClick={handleExam} disabled={!canUseBranch}>
            Generar
          </button>
          <button onClick={handleGenerateStudyPack} disabled={!canUseBranch || !examTopic}>
            Generar pack de estudio
          </button>
          <div className="row" style={{ marginTop: 10 }}>
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
          <div className="row">
            <button onClick={handleExportPdf} disabled={!examId || !canUseBranch}>
              Exportar PDF examen
            </button>
            <button onClick={handleExportDocx} disabled={!examId || !canUseBranch}>
              Exportar DOCX examen
            </button>
          </div>
          <div className="row">
            <button onClick={handleExportAnswerKeyPdf} disabled={!examId || !canUseBranch}>
              Exportar PDF solucionario
            </button>
            <button onClick={handleExportAnswerKeyDocx} disabled={!examId || !canUseBranch}>
              Exportar DOCX solucionario
            </button>
          </div>
          <div className="row" style={{ marginTop: 10 }}>
            <input
              type="file"
              onChange={(e: ChangeEvent<HTMLInputElement>) => setExamSolveFile(e.target.files?.[0] ?? null)}
            />
            <button onClick={handleSolveUploadedExam} disabled={!examSolveFile || !canUseBranch}>
              Subir y resolver examen
            </button>
          </div>
        </div>}
      </div>

      <div className="card">
        <h3>Estado</h3>
        <p>{status || "Sin acciones aún"}</p>
      </div>

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
