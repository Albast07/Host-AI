import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { filter, map, timeout, catchError, of } from 'rxjs';

export const teacherGuard = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (!authService.isAuthenticated()) {
    router.navigate(['/login']);
    return false;
  }

  const currentUser = authService.getCurrentUser();
  if (currentUser) {
    if (currentUser.role === 'teacher') return true;
    if (currentUser.role === 'student') {
      router.navigate(['/']);
      return false;
    }
    router.navigate(['/login']);
    return false;
  }

  return authService.currentUser$.pipe(
    filter((u: any) => u !== null),
    timeout(5000),
    map((user: any) => {
      if (user.role === 'teacher') return true;
      if (user.role === 'student') {
        router.navigate(['/']);
        return false;
      }
      router.navigate(['/login']);
      return false;
    }),
    catchError(() => {
      router.navigate(['/login']);
      return of(false);
    })
  );
};