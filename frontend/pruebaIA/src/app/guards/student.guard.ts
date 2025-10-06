import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

export const studentGuard = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  // Verificar autenticación
  if (!authService.isAuthenticated()) {
    router.navigate(['/login']);
    return false;
  }

  // Verificar que el usuario sea estudiante
  if (authService.isStudent()) {
    return true;
  }

  // Si es profesor, redirigir al dashboard
  if (authService.isTeacher()) {
    router.navigate(['/dashboard']);
    return false;
  }

  // En caso de rol desconocido, redirigir al login
  router.navigate(['/login']);
  return false;
};