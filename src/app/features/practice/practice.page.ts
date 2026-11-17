import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { AnswerFeedback, PracticeSession } from '../../core/models/practice.model';
import { Question, QUESTION_TYPE_LABELS } from '../../core/models/question.model';
import { NotificationService } from '../../core/services/notification.service';
import { PracticeApiService } from '../../core/services/practice-api.service';
import { PreferencesService } from '../../core/services/preferences.service';
import { SessionStorageService } from '../../core/services/session-storage.service';
import { QuestionMediaComponent } from '../../shared/question-media/question-media.component';

@Component({
  selector: 'app-practice-page',
  imports: [RouterLink, QuestionMediaComponent],
  templateUrl: './practice.page.html',
  styleUrl: './practice.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PracticePage {
  private readonly practiceApi = inject(PracticeApiService);
  protected readonly preferences = inject(PreferencesService);
  private readonly storage = inject(SessionStorageService);
  private readonly notifications = inject(NotificationService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly sessionId = this.route.snapshot.paramMap.get('sessionId') ?? '';
  protected readonly session = signal<PracticeSession | null>(null);
  protected readonly question = signal<Question | null>(null);
  protected readonly feedback = signal<AnswerFeedback | null>(null);
  protected readonly selectedKeys = signal<string[]>([]);
  protected readonly loading = signal(true);
  protected readonly submitting = signal(false);
  protected readonly transitioning = signal(false);
  protected readonly showSummary = signal(false);
  protected readonly panelCollapsed = signal(this.readPanelPreference());
  protected readonly typeLabels = QUESTION_TYPE_LABELS;
  protected readonly progress = computed(() => {
    const current = this.session();
    return current ? Math.round((current.answered_items / current.total_items) * 100) : 0;
  });
  protected readonly canSubmit = computed(() => {
    const current = this.question();
    if (!current || this.feedback() || this.submitting()) return false;
    return current.interaction.grading_mode === 'reveal_only' || this.selectedKeys().length > 0;
  });

  private idempotencyKey = crypto.randomUUID();
  private readonly panelPreferenceKey = 'mb230.practice.panel-collapsed';

  constructor() {
    if (!this.sessionId) {
      void this.router.navigate(['/']);
      return;
    }
    this.storage.save(this.sessionId);
    this.preferences.load().pipe(takeUntilDestroyed(this.destroyRef)).subscribe();
    this.loadCurrent();
  }

  protected toggleOption(key: string): void {
    const current = this.question();
    if (!current || this.feedback()) return;
    if (current.question_type === 'multiple_choice') {
      this.selectedKeys.update((keys) =>
        keys.includes(key) ? keys.filter((item) => item !== key) : [...keys, key]
      );
    } else {
      this.selectedKeys.set([key]);
    }
  }

  protected toggleSessionPanel(): void {
    this.panelCollapsed.update((collapsed) => {
      const nextValue = !collapsed;
      localStorage.setItem(this.panelPreferenceKey, String(nextValue));
      return nextValue;
    });
  }

  protected isSelected(key: string): boolean {
    return this.selectedKeys().includes(key);
  }

  protected optionState(key: string): 'correct' | 'incorrect' | 'selected' | 'idle' {
    const result = this.feedback();
    if (!result) return this.isSelected(key) ? 'selected' : 'idle';
    if (result.source_answer.option_keys.includes(key)) return 'correct';
    if (this.isSelected(key)) return 'incorrect';
    return 'idle';
  }

  protected submit(): void {
    const current = this.question();
    if (!current || !this.canSubmit()) return;
    const response =
      current.interaction.grading_mode === 'automatic'
        ? { choice_keys: this.selectedKeys() }
        : { reveal: true };
    this.submitting.set(true);
    this.practiceApi
      .submitAnswer(this.sessionId, current.id, response, this.idempotencyKey)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.submitting.set(false))
      )
      .subscribe((feedback) => {
        this.feedback.set(feedback);
        this.refreshSession();
        if (feedback.is_correct === true) this.notifications.show('Respuesta correcta', 'success');
      });
  }

  protected next(): void {
    const result = this.feedback();
    if (result?.session_status === 'completed') {
      this.showSummary.set(true);
      this.storage.clear();
      return;
    }
    this.feedback.set(null);
    this.selectedKeys.set([]);
    this.idempotencyKey = crypto.randomUUID();
    this.loadCurrent();
  }

  protected discardAndContinue(action: 'skip' | 'repeat'): void {
    const currentQuestion = this.question();
    if (!currentQuestion || !this.feedback() || this.transitioning()) return;
    this.transitioning.set(true);
    this.practiceApi
      .discardAnswer(this.sessionId, currentQuestion.id, action)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.transitioning.set(false))
      )
      .subscribe((session) => {
        this.session.set(session);
        this.feedback.set(null);
        this.selectedKeys.set([]);
        this.idempotencyKey = crypto.randomUUID();
        if (action === 'skip' && session.status === 'completed') {
          this.showSummary.set(true);
          this.storage.clear();
          return;
        }
        this.loadCurrent();
      });
  }

  private loadCurrent(): void {
    this.loading.set(true);
    this.practiceApi
      .getSession(this.sessionId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((session) => {
        this.session.set(session);
        if (session.status === 'completed') {
          this.loading.set(false);
          this.showSummary.set(true);
          return;
        }
        this.practiceApi
          .getNextQuestion(this.sessionId)
          .pipe(
            takeUntilDestroyed(this.destroyRef),
            finalize(() => this.loading.set(false))
          )
          .subscribe((question) => this.question.set(question));
      });
  }

  private refreshSession(): void {
    this.practiceApi
      .getSession(this.sessionId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((session) => this.session.set(session));
  }

  private readPanelPreference(): boolean {
    return localStorage.getItem('mb230.practice.panel-collapsed') === 'true';
  }
}
