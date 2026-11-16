import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { finalize } from 'rxjs';

import { Exam } from '../../core/models/exam.model';
import { ExamApiService } from '../../core/services/exam-api.service';
import { NotificationService } from '../../core/services/notification.service';
import { PracticeSession } from '../../core/models/practice.model';
import { AuthService } from '../../core/services/auth.service';
import { PracticeApiService } from '../../core/services/practice-api.service';
import { SessionStorageService } from '../../core/services/session-storage.service';

@Component({
  selector: 'app-home-page',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './home.page.html',
  styleUrl: './home.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class HomePage {
  private readonly examApi = inject(ExamApiService);
  private readonly practiceApi = inject(PracticeApiService);
  protected readonly auth = inject(AuthService);
  private readonly storage = inject(SessionStorageService);
  private readonly notifications = inject(NotificationService);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);

  protected readonly exam = signal<Exam | null>(null);
  protected readonly loading = signal(true);
  protected readonly starting = signal(false);
  protected readonly activeSessionId = signal(this.storage.get());
  protected readonly activeSessions = signal<PracticeSession[]>([]);
  protected readonly sessionForm = this.formBuilder.nonNullable.group({
    fromOrder: [1, [Validators.required, Validators.min(1), Validators.max(463)]],
    toOrder: [463, [Validators.required, Validators.min(1), Validators.max(463)]]
  });

  constructor() {
    this.examApi
      .getExam()
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.loading.set(false))
      )
      .subscribe((exam) => this.exam.set(exam));
    if (this.auth.isAuthenticated()) {
      this.practiceApi.getSessions().pipe(takeUntilDestroyed(this.destroyRef)).subscribe((sessions) => {
        this.activeSessions.set(sessions.filter((item) => item.status === 'active'));
      });
    }
  }

  protected setPreset(size: number): void {
    this.sessionForm.setValue({ fromOrder: 1, toOrder: size });
  }

  protected startSession(): void {
    if (!this.auth.isAuthenticated()) {
      void this.router.navigate(['/access'], { queryParams: { returnUrl: '/' } });
      return;
    }
    if (this.sessionForm.invalid) {
      this.sessionForm.markAllAsTouched();
      this.notifications.show('Revisa el intervalo de preguntas.', 'error');
      return;
    }
    const { fromOrder, toOrder } = this.sessionForm.getRawValue();
    if (toOrder < fromOrder) {
      this.notifications.show('La pregunta final debe ser posterior a la inicial.', 'error');
      return;
    }

    this.starting.set(true);
    this.practiceApi
      .createSession({
        exam_slug: 'mb-230',
        mode: 'sequential',
        from_order: fromOrder,
        to_order: toOrder
      })
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.starting.set(false))
      )
      .subscribe((session) => {
        this.storage.save(session.id);
        void this.router.navigate(['/practice', session.id]);
      });
  }
}
