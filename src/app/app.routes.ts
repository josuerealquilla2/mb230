import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    title: 'Inicio · MB-230 Focus',
    loadComponent: () => import('./features/home/home.page').then((m) => m.HomePage)
  },
  {
    path: 'access',
    title: 'Acceso · MB-230 Focus',
    loadComponent: () => import('./features/auth/auth.page').then((m) => m.AuthPage)
  },
  {
    path: 'questions',
    title: 'Explorar preguntas · MB-230 Focus',
    loadComponent: () => import('./features/questions/questions.page').then((m) => m.QuestionsPage)
  },
  {
    path: 'topics',
    title: 'Práctica por temas · MB-230 Focus',
    loadComponent: () => import('./features/topic-practice/topic-practice.page').then((m) => m.TopicPracticePage)
  },
  {
    path: 'saved',
    title: 'Preguntas guardadas · MB-230 Focus',
    canActivate: [authGuard],
    loadComponent: () => import('./features/saved-questions/saved-questions.page').then((m) => m.SavedQuestionsPage)
  },
  {
    path: 'practice/:sessionId',
    title: 'Sesión de práctica · MB-230 Focus',
    canActivate: [authGuard],
    loadComponent: () => import('./features/practice/practice.page').then((m) => m.PracticePage)
  },
  {
    path: 'settings',
    title: 'Configuración · MB-230 Focus',
    canActivate: [authGuard],
    loadComponent: () => import('./features/settings/settings.page').then((m) => m.SettingsPage)
  },
  { path: '**', redirectTo: '' }
];
