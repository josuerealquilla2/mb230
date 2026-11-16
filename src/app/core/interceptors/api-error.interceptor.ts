import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';

import { NotificationService } from '../services/notification.service';

export const apiErrorInterceptor: HttpInterceptorFn = (request, next) => {
  const notifications = inject(NotificationService);
  return next(request).pipe(
    catchError((error: HttpErrorResponse) => {
      const detail = error.error?.error?.detail;
      const fieldMessage = error.error && typeof error.error === 'object'
        ? Object.values(error.error).flat().find((value) => typeof value === 'string')
        : null;
      const message =
        typeof detail === 'string'
          ? detail
          : typeof fieldMessage === 'string'
            ? fieldMessage
            : error.status === 401
              ? 'Inicia sesión para continuar.'
          : error.status === 0
            ? 'No se pudo conectar con la API Django. Comprueba que esté iniciada.'
            : 'No se pudo completar la operación. Inténtalo de nuevo.';
      notifications.show(message, 'error');
      return throwError(() => error);
    })
  );
};
