export type QuestionType =
  | 'single_choice'
  | 'multiple_choice'
  | 'yes_no'
  | 'drag_drop'
  | 'hotspot';

export interface QuestionOption {
  key: string;
  position: number;
  text: string;
  text_es: string;
}

export interface QuestionMedia {
  position: number;
  role: string;
  url: string;
  sha256: string;
  mime_type: string;
  width: number;
  height: number;
  source_page: number;
}

export interface QuestionInteraction {
  kind: QuestionType;
  grading_mode: 'automatic' | 'reveal_only';
  response_schema: Record<string, unknown>;
}

export interface Question {
  id: string;
  exam_slug: string;
  pdf_order: number;
  source_question_number: number;
  question_type: QuestionType;
  language: string;
  prompt_text: string;
  prompt_text_es: string;
  options: QuestionOption[];
  interaction: QuestionInteraction;
  question_media: QuestionMedia[];
  source_pages: { start: number; end: number };
}

export interface QuestionPage {
  data: Question[];
  next_after_order: number | null;
  count: number;
}

export interface QuestionFilters {
  afterOrder?: number;
  limit?: number;
  questionType?: QuestionType | '';
}

export const QUESTION_TYPE_LABELS: Record<QuestionType, string> = {
  single_choice: 'Respuesta única',
  multiple_choice: 'Selección múltiple',
  yes_no: 'Sí o no',
  drag_drop: 'Arrastrar y soltar',
  hotspot: 'Pregunta visual'
};
