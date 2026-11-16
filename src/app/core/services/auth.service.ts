import { HttpClient } from '@angular/common/http';
import { computed, inject, Injectable, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { environment } from '../../../environments/environment';
import { AuthResponse, UserAccount } from '../models/auth.model';

const TOKEN_KEY = 'mb230.auth.token';
const USER_KEY = 'mb230.auth.user';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly userState = signal<UserAccount | null>(this.readUser());

  readonly user = this.userState.asReadonly();
  readonly isAuthenticated = computed(() => !!this.userState() && !!this.token());

  token(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }

  register(username: string, password: string): Observable<AuthResponse> {
    return this.http
      .post<AuthResponse>(`${environment.apiUrl}/auth/register`, { username, password })
      .pipe(tap((response) => this.persist(response)));
  }

  login(username: string, password: string): Observable<AuthResponse> {
    return this.http
      .post<AuthResponse>(`${environment.apiUrl}/auth/login`, { username, password })
      .pipe(tap((response) => this.persist(response)));
  }

  logout(): void {
    const request = this.http.post<void>(`${environment.apiUrl}/auth/logout`, {});
    request.subscribe({ error: () => undefined });
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    this.userState.set(null);
  }

  private persist(response: AuthResponse): void {
    localStorage.setItem(TOKEN_KEY, response.token);
    localStorage.setItem(USER_KEY, JSON.stringify(response.user));
    this.userState.set(response.user);
  }

  private readUser(): UserAccount | null {
    const raw = localStorage.getItem(USER_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as UserAccount;
    } catch {
      localStorage.removeItem(USER_KEY);
      return null;
    }
  }
}
