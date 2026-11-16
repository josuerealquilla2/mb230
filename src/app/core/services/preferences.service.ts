import { HttpClient } from '@angular/common/http';
import { effect, inject, Injectable, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { environment } from '../../../environments/environment';
import { ThemePreference, UserPreference } from '../models/auth.model';

const THEME_KEY = 'mb230.theme';
const defaults: UserPreference = {
  theme: 'system',
  show_translation: true,
  default_session_size: 463,
  onboarding_completed: false,
};

@Injectable({ providedIn: 'root' })
export class PreferencesService {
  private readonly http = inject(HttpClient);
  readonly preferences = signal<UserPreference>({
    ...defaults,
    theme: (localStorage.getItem(THEME_KEY) as ThemePreference | null) ?? 'system',
  });

  constructor() {
    effect(() => this.applyTheme(this.preferences().theme));
  }

  load(): Observable<UserPreference> {
    return this.http
      .get<UserPreference>(`${environment.apiUrl}/me/preferences`)
      .pipe(tap((value) => this.preferences.set(value)));
  }

  save(changes: Partial<UserPreference>): Observable<UserPreference> {
    return this.http
      .patch<UserPreference>(`${environment.apiUrl}/me/preferences`, changes)
      .pipe(tap((value) => this.preferences.set(value)));
  }

  setLocalTheme(theme: ThemePreference): void {
    this.preferences.update((current) => ({ ...current, theme }));
    localStorage.setItem(THEME_KEY, theme);
  }

  private applyTheme(theme: ThemePreference): void {
    const dark = theme === 'dark' || (theme === 'system' && matchMedia('(prefers-color-scheme: dark)').matches);
    document.documentElement.dataset['theme'] = dark ? 'dark' : 'light';
    document.documentElement.setAttribute('data-bs-theme', dark ? 'dark' : 'light');
  }
}
