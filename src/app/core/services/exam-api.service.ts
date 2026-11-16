import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { Exam } from '../models/exam.model';
import { Question, QuestionFilters, QuestionPage } from '../models/question.model';

@Injectable({ providedIn: 'root' })
export class ExamApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiUrl;

  getExam(slug = 'mb-230'): Observable<Exam> {
    return this.http.get<Exam>(`${this.baseUrl}/exams/${slug}`);
  }

  getQuestion(questionId: string): Observable<Question> {
    return this.http.get<Question>(`${this.baseUrl}/questions/${questionId}`);
  }

  getQuestions(slug = 'mb-230', filters: QuestionFilters = {}): Observable<QuestionPage> {
    let params = new HttpParams()
      .set('after_order', String(filters.afterOrder ?? 0))
      .set('limit', String(filters.limit ?? 20));
    if (filters.questionType) {
      params = params.set('question_type', filters.questionType);
    }
    return this.http.get<QuestionPage>(`${this.baseUrl}/exams/${slug}/questions`, { params });
  }
}

