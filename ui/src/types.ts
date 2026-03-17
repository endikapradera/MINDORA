export type Branch = {
  name: string;
  path: string;
};

export type ChunkResult = {
  chunk_id: number;
  document_id: number;
  chunk_index: number;
  filename: string;
  path: string;
  score: number;
  text: string;
};

export type QueryResponse = {
  results: ChunkResult[];
};

export type AskResponse = {
  answer: string;
  contexts: string[];
  sources: string[];
  session_id?: string | null;
};

export type StudyPackResponse = {
  topic: string;
  summary_short: string;
  summary_long: string;
  key_ideas: string[];
  concepts_to_memorize: string[];
  possible_exam_questions: string[];
  common_mistakes: string[];
  mini_test: string[];
  sources: string[];
};

export type ResponseStyle = "auto" | "corta" | "detallada" | "pasos" | "detallada_pasos" | "examen" | "profesor" | "companero";

export type LearnPhrasePayload = {
  phrase: string;
  intent: "explicar" | "resumir" | "comparar" | "ejemplo" | "definir" | "pasos" | "general";
  response_style: ResponseStyle;
};

export type FeedbackPayload = {
  question: string;
  response_style: ResponseStyle;
  useful: boolean;
  answer_text?: string;
  branch?: string;
};

export type ExamGenerateResponse = {
  exam_id: string;
  filename: string;
  exam_content: string;
  answer_key_content: string;
};

export type ExamType = "test_simple" | "test_multiple" | "desarrollo" | "mixto";

export type ExportKind = "exam" | "answer_key";

export type ExamExportResponse = {
  path: string;
};

export type ExamSolveUploadResponse = {
  solutions: string;
};

export type SimulationQuestion = {
  number: number;
  type: string;
  statement: string;
  options: string[];
};

export type ExamSimulationStartResponse = {
  simulation_id: string;
  exam_id: string;
  topic: string;
  duration_minutes: number;
  started_at: string;
  expires_at: string;
  questions: SimulationQuestion[];
};

export type SimulationResultItem = {
  number: number;
  type: string;
  statement: string;
  student_answer: string;
  expected_answer: string;
  correct: boolean;
  feedback: string;
};

export type ExamSimulationSubmitResponse = {
  simulation_id: string;
  exam_id: string;
  topic: string;
  total_questions: number;
  answered_questions: number;
  correct_answers: number;
  score_percent: number;
  status: string;
  weak_topics: string[];
  results: SimulationResultItem[];
};

export type ExamSimulationHistoryItem = {
  simulation_id: string;
  exam_id: string;
  topic: string;
  started_at: string;
  submitted_at?: string | null;
  status: string;
  score_percent?: number | null;
};

export type ExamSimulationHistoryResponse = {
  items: ExamSimulationHistoryItem[];
};

export type DictionaryEntry = {
  phrase: string;
  intent: string;
  response_style: string;
};

export type DictionaryResponse = {
  entries: DictionaryEntry[];
};

export type DailyRecommendationItem = {
  topic: string;
  fail_count: number;
  last_failed: string;
  suggestion: string;
};

export type DailyRecommendationsResponse = {
  recommendations: DailyRecommendationItem[];
  message: string;
};

export type DocumentItem = {
  id: number;
  filename: string;
  path: string;
  created_at: string;
};

export type DocumentListResponse = {
  documents: DocumentItem[];
};
