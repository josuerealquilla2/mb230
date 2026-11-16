export interface UserAccount {
  id: number;
  username: string;
}

export interface AuthResponse {
  token: string;
  user: UserAccount;
}

export type ThemePreference = 'system' | 'light' | 'dark';

export interface UserPreference {
  theme: ThemePreference;
  show_translation: boolean;
  default_session_size: 10 | 20 | 50 | 463;
  onboarding_completed: boolean;
}
