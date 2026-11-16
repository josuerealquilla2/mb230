import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-auth-page',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './auth.page.html',
  styleUrl: './auth.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AuthPage {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly fb = inject(FormBuilder);

  protected readonly mode = signal<'login' | 'register'>('login');
  protected readonly submitting = signal(false);
  protected readonly form = this.fb.nonNullable.group({
    username: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(40)]],
    password: ['', [Validators.required, Validators.minLength(8), Validators.maxLength(128)]],
  });

  constructor() {
    if (this.auth.isAuthenticated()) void this.router.navigate(['/']);
  }

  protected changeMode(mode: 'login' | 'register'): void {
    this.mode.set(mode);
  }

  protected submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const { username, password } = this.form.getRawValue();
    const request =
      this.mode() === 'register'
        ? this.auth.register(username, password)
        : this.auth.login(username, password);
    this.submitting.set(true);
    request.pipe(finalize(() => this.submitting.set(false))).subscribe(() => {
      const destination = this.route.snapshot.queryParamMap.get('returnUrl') || '/';
      void this.router.navigateByUrl(destination);
    });
  }
}
