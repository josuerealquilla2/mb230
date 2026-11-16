import { HttpClient, HttpHeaders } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { Question } from '../models/question.model';
import { AnswerFeedback, PracticeSession, PracticeSessionCreate } from '../models/practice.model';

@Injectable({ providedIn: 'root' })
export class PracticeApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/practice-sessions`;

  createSession(payload: PracticeSessionCreate): Observable<PracticeSession> {
    return this.http.post<PracticeSession>(this.baseUrl, payload);
  }

  getSessions(): Observable<PracticeSession[]> {
    return this.http.get<PracticeSession[]>(this.baseUrl);
  }

  getSession(sessionId: string): Observable<PracticeSession> {
    return this.http.get<PracticeSession>(`${this.baseUrl}/${sessionId}`);
  }

  getNextQuestion(sessionId: string): Observable<Question> {
    return this.http.get<Question>(`${this.baseUrl}/${sessionId}/next`);
  }

  submitAnswer(
    sessionId: string,
    questionId: string,
    response: Record<string, unknown>,
    idempotencyKey: string
  ): Observable<AnswerFeedback> {
    const headers = new HttpHeaders({ 'Idempotency-Key': idempotencyKey });
    return this.http.post<AnswerFeedback>(
      `${this.baseUrl}/${sessionId}/answers`,
      { question_id: questionId, response },
      { headers }
    );
  }
}
