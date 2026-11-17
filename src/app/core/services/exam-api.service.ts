import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { Exam } from '../models/exam.model';
import { Question, QuestionFilters, QuestionPage, QuestionTopic } from '../models/question.model';
import { QuestionFeedback } from '../models/practice.model';

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
    if (filters.topic) params = params.set('topic', filters.topic);
    return this.http.get<QuestionPage>(`${this.baseUrl}/exams/${slug}/questions`, { params });
  }

  getTopics(slug = 'mb-230'): Observable<QuestionTopic[]> {
    return this.http.get<QuestionTopic[]>(`${this.baseUrl}/exams/${slug}/topics`);
  }

  checkQuestion(questionId: string, choiceKeys: string[]): Observable<QuestionFeedback> {
    return this.http.post<QuestionFeedback>(`${this.baseUrl}/questions/${questionId}/check`, {
      question_id: questionId,
      response: { choice_keys: choiceKeys }
    });
  }

  getSavedQuestions(): Observable<Question[]> {
    return this.http.get<Question[]>(`${this.baseUrl}/me/saved-questions`);
  }

  saveQuestion(questionId: string): Observable<{ saved: boolean }> {
    return this.http.put<{ saved: boolean }>(`${this.baseUrl}/me/saved-questions/${questionId}`, {});
  }

  removeSavedQuestion(questionId: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/me/saved-questions/${questionId}`);
  }
}
