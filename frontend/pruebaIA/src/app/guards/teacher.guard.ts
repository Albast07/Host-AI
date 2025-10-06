import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

export const teacherGuard = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  // Verificar autenticación
  if (!authService.isAuthenticated()) {
    router.navigate(['/login']);
    return false;
  }

  // Verificar que el usuario sea profesor
  if (authService.isTeacher()) {
    return true;
  }

  // Si es estudiante, redirigir al journal (ruta raíz)
  if (authService.isStudent()) {
    router.navigate(['/']);
    return false;
  }

  // En caso de rol desconocido, redirigir al login
  router.navigate(['/login']);
  return false;
};