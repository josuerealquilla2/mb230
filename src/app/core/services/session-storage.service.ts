import { Injectable } from '@angular/core';

const SESSION_KEY = 'mb230.activeSession';

@Injectable({ providedIn: 'root' })
export class SessionStorageService {
  save(sessionId: string): void {
    localStorage.setItem(SESSION_KEY, sessionId);
  }

  get(): string | null {
    return localStorage.getItem(SESSION_KEY);
  }

  clear(): void {
    localStorage.removeItem(SESSION_KEY);
  }
}

