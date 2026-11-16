import { Injectable, signal } from '@angular/core';

export interface Notice {
  message: string;
  tone: 'error' | 'success' | 'info';
}

@Injectable({ providedIn: 'root' })
export class NotificationService {
  readonly notice = signal<Notice | null>(null);
  private timeoutId: ReturnType<typeof setTimeout> | undefined;

  show(message: string, tone: Notice['tone'] = 'info'): void {
    clearTimeout(this.timeoutId);
    this.notice.set({ message, tone });
    this.timeoutId = setTimeout(() => this.notice.set(null), 4500);
  }

  dismiss(): void {
    clearTimeout(this.timeoutId);
    this.notice.set(null);
  }
}

