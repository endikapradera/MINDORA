export type Branch = {
  name: string;
  path: string;
};

export type ChunkResult = {
  chunk_id: number;
  document_id: number;
  score: number;
  text: string;
};

export type QueryResponse = {
  results: ChunkResult[];
};

export type AskResponse = {
  answer: string;
  contexts: string[];
};

export type ExamGenerateResponse = {
  exam_id: string;
  filename: string;
  content: string;
};

export type ExamExportResponse = {
  path: string;
};
