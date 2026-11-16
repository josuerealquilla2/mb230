import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { ThemePreference, UserPreference } from '../../core/models/auth.model';
import { NotificationService } from '../../core/services/notification.service';
import { PreferencesService } from '../../core/services/preferences.service';

@Component({
  selector: 'app-settings-page',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './settings.page.html',
  styleUrl: './settings.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SettingsPage {
  private readonly preferencesService = inject(PreferencesService);
  private readonly notifications = inject(NotificationService);
  private readonly fb = inject(FormBuilder);
  protected readonly loading = signal(true);
  protected readonly saving = signal(false);
  protected readonly form = this.fb.nonNullable.group({
    theme: ['system' as ThemePreference],
    show_translation: [true],
    default_session_size: [463 as UserPreference['default_session_size']],
    onboarding_completed: [false],
  });

  constructor() {
    this.preferencesService.load().pipe(finalize(() => this.loading.set(false))).subscribe((value) => {
      this.form.setValue(value);
      this.preferencesService.setLocalTheme(value.theme);
    });
  }

  protected previewTheme(): void {
    this.preferencesService.setLocalTheme(this.form.controls.theme.value);
  }

  protected save(): void {
    this.saving.set(true);
    this.preferencesService.save(this.form.getRawValue()).pipe(finalize(() => this.saving.set(false))).subscribe(() => {
      this.notifications.show('Configuración guardada.', 'success');
    });
  }
}
