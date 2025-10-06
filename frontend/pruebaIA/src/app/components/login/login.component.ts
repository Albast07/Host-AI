import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService, LoginRequest } from '../../services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss']
})
export class LoginComponent {
  loginData: LoginRequest = {
    username: '',
    password: ''
  };
  
  userType: 'student' | 'teacher' = 'student'; // Toggle para tipo de usuario
  isLoading = false;
  errorMessage = '';
  successMessage = '';

  constructor(
    public authService: AuthService,
    private router: Router
  ) {
    // Si ya está autenticado, redirigir al dashboard
    if (this.authService.isAuthenticated()) {
      this.router.navigate(['/']);
    }
  }

  onSubmit() {
    if (!this.loginData.username || !this.loginData.password) {
      this.errorMessage = 'Por favor completa todos los campos';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';
    this.successMessage = '';

    this.authService.login(this.loginData).subscribe({
      next: (response: any) => {
        // Verificar que el rol del usuario coincida con el tipo seleccionado
        const currentUser = this.authService.getCurrentUser();
        if (currentUser && currentUser.role !== this.userType) {
          this.errorMessage = `Este usuario no es ${this.userType === 'student' ? 'estudiante' : 'profesor'}. Verifica el tipo de usuario seleccionado.`;
          this.authService.logout(); // Deslogear si el rol no coincide
          this.isLoading = false;
          return;
        }

        this.successMessage = response.message || 'Login exitoso';
        // Redirigir según el tipo de usuario
        setTimeout(() => {
          if (this.userType === 'teacher') {
            this.router.navigate(['/dashboard']); // Los profesores van al dashboard
          } else {
            this.router.navigate(['/']); // Los estudiantes van al journal
          }
        }, 1000);
      },
      error: (error: any) => {
        this.isLoading = false;
        console.error('Error en login:', error);
        if (error.error && error.error.non_field_errors) {
          this.errorMessage = error.error.non_field_errors[0];
        } else if (error.error && error.error.error) {
          this.errorMessage = error.error.error;
        } else {
          this.errorMessage = 'Error al iniciar sesión. Verifica tus credenciales.';
        }
      },
      complete: () => {
        this.isLoading = false;
      }
    });
  }

  goToRegister() {
    this.router.navigate(['/register']);
  }
  goToJournal() {
    this.router.navigate(['/']);
  }
}