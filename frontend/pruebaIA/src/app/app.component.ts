import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, RouterLink, RouterLinkActive, Router, NavigationEnd } from '@angular/router';
import { AuthService } from './services/auth.service';
import { filter } from 'rxjs/operators';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent {
  title = 'Diario Emocional IA';
  showNavbar = true;

  constructor(
    private router: Router,
    public authService: AuthService
  ) {
    // Escuchar cambios de ruta para ocultar navbar en login/register
    this.router.events
      .pipe(filter(event => event instanceof NavigationEnd))
      .subscribe((event: NavigationEnd) => {
        this.showNavbar = !this.isAuthRoute(event.url);
      });
  }

  private isAuthRoute(url: string): boolean {
    return url.includes('/login') || url.includes('/register');
  }

  isStudent(): boolean {
    return this.authService.isAuthenticated() && this.authService.isStudent();
  }

  isTeacher(): boolean {
    return this.authService.isAuthenticated() && this.authService.isTeacher();
  }

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }
}