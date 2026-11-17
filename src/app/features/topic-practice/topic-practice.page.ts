import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize, forkJoin } from 'rxjs';

import { Question, QuestionTopic, QuestionType } from '../../core/models/question.model';
import { QuestionFeedback } from '../../core/models/practice.model';
import { AuthService } from '../../core/services/auth.service';
import { ExamApiService } from '../../core/services/exam-api.service';
import { QuestionMediaComponent } from '../../shared/question-media/question-media.component';

@Component({
  selector: 'app-topic-practice-page',
  imports: [ReactiveFormsModule, QuestionMediaComponent],
  templateUrl: './topic-practice.page.html',
  styleUrl: './topic-practice.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TopicPracticePage {
  private readonly api = inject(ExamApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly fb = inject(FormBuilder);
  protected readonly auth = inject(AuthService);
  protected readonly topics = signal<QuestionTopic[]>([]);
  protected readonly questions = signal<Question[]>([]);
  protected readonly index = signal(0);
  protected readonly selected = signal<string[]>([]);
  protected readonly feedback = signal<QuestionFeedback | null>(null);
  protected readonly loading = signal(true);
  protected readonly checking = signal(false);
  protected readonly savedIds = signal(new Set<string>());
  protected readonly form = this.fb.nonNullable.group({ topic: ['', Validators.required] });

  constructor() {
    const requests: { topics: ReturnType<ExamApiService['getTopics']>; saved?: ReturnType<ExamApiService['getSavedQuestions']> } = { topics: this.api.getTopics() };
    if (this.auth.isAuthenticated()) requests.saved = this.api.getSavedQuestions();
    forkJoin(requests).pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.loading.set(false))).subscribe((result) => {
      this.topics.set(result.topics);
      this.savedIds.set(new Set(result.saved?.map((question) => question.id) ?? []));
      if (result.topics[0]) this.form.controls.topic.setValue(result.topics[0].id);
    });
  }

  protected current(): Question | null { return this.questions()[this.index()] ?? null; }
  protected start(): void {
    if (this.form.invalid) return;
    this.loading.set(true);
    this.api.getQuestions('mb-230', { topic: this.form.controls.topic.value, limit: 100 })
      .pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.loading.set(false)))
      .subscribe((page) => { this.questions.set(page.data); this.index.set(0); this.resetQuestion(); });
  }
  protected select(key: string, type: QuestionType): void {
    if (this.feedback()) return;
    if (type === 'multiple_choice') this.selected.update((keys) => keys.includes(key) ? keys.filter((item) => item !== key) : [...keys, key]);
    else this.selected.set([key]);
  }
  protected check(): void {
    const question = this.current();
    if (!question || (question.interaction.grading_mode === 'automatic' && !this.selected().length)) return;
    this.checking.set(true);
    this.api.checkQuestion(question.id, this.selected()).pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.checking.set(false))).subscribe((feedback) => this.feedback.set(feedback));
  }
  protected next(): void { if (this.index() < this.questions().length - 1) { this.index.update((value) => value + 1); this.resetQuestion(); } }
  protected toggleSaved(): void {
    const question = this.current(); if (!question || !this.auth.isAuthenticated()) return;
    const saved = this.savedIds().has(question.id);
    const update = () => this.savedIds.update((ids) => {
      const next = new Set(ids); saved ? next.delete(question.id) : next.add(question.id); return next;
    });
    if (saved) this.api.removeSavedQuestion(question.id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe(update);
    else this.api.saveQuestion(question.id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe(update);
  }
  private resetQuestion(): void { this.selected.set([]); this.feedback.set(null); }
}
