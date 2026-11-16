import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { finalize } from 'rxjs';

import {
  Question,
  QuestionType,
  QUESTION_TYPES,
  QUESTION_TYPE_LABELS
} from '../../core/models/question.model.constants';
import { ExamApiService } from '../../core/services/exam-api.service';
import { QuestionMediaComponent } from '../../shared/question-media/question-media.component';

@Component({
  selector: 'app-questions-page',
  imports: [ReactiveFormsModule, QuestionMediaComponent],
  templateUrl: './questions.page.html',
  styleUrl: './questions.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class QuestionsPage {
  private readonly api = inject(ExamApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);

  protected readonly questions = signal<Question[]>([]);
  protected readonly loading = signal(false);
  protected readonly nextAfterOrder = signal<number | null>(0);
  protected readonly typeOptions = QUESTION_TYPES;
  protected readonly typeLabels = QUESTION_TYPE_LABELS;
  protected readonly filterForm = this.formBuilder.nonNullable.group({
    questionType: ['' as QuestionType | ''],
    limit: [12]
  });

  constructor() {
    this.load(true);
  }

  protected applyFilters(): void {
    this.load(true);
  }

  protected load(reset = false): void {
    if (this.loading()) return;
    const cursor = reset ? 0 : this.nextAfterOrder();
    if (cursor === null) return;
    if (reset) {
      this.questions.set([]);
      this.nextAfterOrder.set(0);
    }
    const { questionType, limit } = this.filterForm.getRawValue();
    this.loading.set(true);
    this.api
      .getQuestions('mb-230', {
        afterOrder: cursor,
        limit,
        questionType: questionType || undefined
      })
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.loading.set(false))
      )
      .subscribe((page) => {
        this.questions.update((current) => (reset ? page.data : [...current, ...page.data]));
        this.nextAfterOrder.set(page.next_after_order);
      });
  }

  protected labelFor(type: QuestionType): string {
    return this.typeLabels[type];
  }
}

