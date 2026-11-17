import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { finalize } from 'rxjs';
import { Question } from '../../core/models/question.model';
import { ExamApiService } from '../../core/services/exam-api.service';
import { QuestionMediaComponent } from '../../shared/question-media/question-media.component';

@Component({
  selector: 'app-saved-questions-page',
  imports: [QuestionMediaComponent],
  templateUrl: './saved-questions.page.html',
  styleUrl: './saved-questions.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class SavedQuestionsPage {
  private readonly api = inject(ExamApiService);
  private readonly destroyRef = inject(DestroyRef);
  protected readonly questions = signal<Question[]>([]);
  protected readonly loading = signal(true);
  constructor() { this.api.getSavedQuestions().pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.loading.set(false))).subscribe((items) => this.questions.set(items)); }
  protected remove(question: Question): void { this.api.removeSavedQuestion(question.id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => this.questions.update((items) => items.filter((item) => item.id !== question.id))); }
}
