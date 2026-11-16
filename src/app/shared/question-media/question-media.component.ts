import { ChangeDetectionStrategy, Component, input, signal } from '@angular/core';

import { QuestionMedia } from '../../core/models/question.model';

@Component({
  selector: 'app-question-media',
  templateUrl: './question-media.component.html',
  styleUrl: './question-media.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class QuestionMediaComponent {
  readonly media = input.required<QuestionMedia[]>();
  readonly alt = input('Recurso visual de la pregunta');
  protected readonly expanded = signal<QuestionMedia | null>(null);
}

