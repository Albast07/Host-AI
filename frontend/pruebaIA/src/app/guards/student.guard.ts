import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { filter, firstValueFrom, map, timeout, catchError, of } from 'rxjs';

export const studentGuard = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  // If not authenticated, redirect immediately
  if (!authService.isAuthenticated()) {
    router.navigate(['/login']);
    return false;
  }

  // If we already have the current user loaded, evaluate role synchronously
  const currentUser = authService.getCurrentUser();
  if (currentUser) {
    if (currentUser.role === 'student') return true;
    if (currentUser.role === 'teacher') {
      router.navigate(['/dashboard']);
      return false;
    }
    router.navigate(['/login']);
    return false;
  }

  // Otherwise wait for currentUser$ to emit a non-null value (i.e., after loadCurrentUser).
  // Use a timeout to avoid hanging navigation indefinitely.
  return authService.currentUser$.pipe(
    filter((u: any) => u !== null),
    timeout(5000),
    map((user: any) => {
      if (user.role === 'student') return true;
      if (user.role === 'teacher') {
        router.navigate(['/dashboard']);
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