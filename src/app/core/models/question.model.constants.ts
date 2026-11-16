import { Question, QuestionType, QUESTION_TYPE_LABELS as LABELS } from './question.model';

export type { Question, QuestionType };

export const QUESTION_TYPES: QuestionType[] = [
  'single_choice',
  'multiple_choice',
  'yes_no',
  'drag_drop',
  'hotspot'
];

export const QUESTION_TYPE_LABELS = LABELS;

