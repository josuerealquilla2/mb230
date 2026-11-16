import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { Router } from '@angular/router';

import { AuthService } from './core/services/auth.service';
import { NotificationService } from './core/services/notification.service';
import { PreferencesService } from './core/services/preferences.service';

@Component({
  selector: 'app-root',
  imports: [RouterLink, RouterLinkActive, RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class App {
  protected readonly notifications = inject(NotificationService);
  protected readonly auth = inject(AuthService);
  protected readonly preferences = inject(PreferencesService);
  private readonly router = inject(Router);

  protected toggleTheme(): void {
    const next = document.documentElement.dataset['theme'] === 'dark' ? 'light' : 'dark';
    this.preferences.setLocalTheme(next);
  }

  protected logout(): void {
    this.auth.logout();
    void this.router.navigate(['/access']);
  }
}
