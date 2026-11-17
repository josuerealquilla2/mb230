import { QuestionMedia } from './question.model';

export interface PracticeSessionCreate {
  exam_slug: string;
  mode: 'sequential';
  from_order: number;
  to_order: number;
}

export interface PracticeSession {
  id: string;
  exam_slug: string;
  mode: 'sequential';
  current_position: number;
  total_items: number;
  answered_items: number;
  correct_items: number;
  status: 'active' | 'completed';
  created_at: string;
  updated_at: string | null;
}

export interface CommunityComment {
  position: number;
  raw_text: string;
  raw_text_es: string;
  selected_answer: string | null;
  source_pages: number[];
}

export interface AnswerReference {
  position: number;
  raw_text: string;
  url: string | null;
}

export interface AnswerFeedback {
  question_id: string;
  is_correct: boolean | null;
  grading_mode: 'automatic' | 'reveal_only';
  source_answer: {
    raw_text: string;
    option_keys: string[];
    status: string;
  };
  source_answer_raw: string;
  explanation_raw: string;
  community_discussion_raw: string;
  references: AnswerReference[];
  community_comments: CommunityComment[];
  answer_media: QuestionMedia[];
  session_status: 'active' | 'completed';
  next_position: number | null;
}

export type QuestionFeedback = Omit<AnswerFeedback, 'session_status' | 'next_position'>;
