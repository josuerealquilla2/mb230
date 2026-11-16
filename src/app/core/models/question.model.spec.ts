import { describe, expect, it } from 'vitest';

import { QUESTION_TYPE_LABELS, QuestionType } from './question.model';

describe('question model', () => {
  it('defines a visible label for every API question type', () => {
    const types: QuestionType[] = [
      'single_choice',
      'multiple_choice',
      'yes_no',
      'drag_drop',
      'hotspot'
    ];

    expect(types.every((type) => QUESTION_TYPE_LABELS[type].length > 0)).toBe(true);
  });
});

