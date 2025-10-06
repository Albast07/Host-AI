import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService, RegisterRequest } from '../../services/auth.service';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './register.component.html',
  styleUrls: ['./register.component.scss']
})
export class RegisterComponent {
  registerData: RegisterRequest = {
    username: '',
    email: '',
    password: '',
    password_confirm: '',
    first_name: '',
    last_name: '',
    role: 'student',
    fecha_de_nacimiento: ''
  };
  
  confirmPassword = '';
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
    // Validaciones
    if (!this.registerData.username || !this.registerData.email || !this.registerData.password || !this.registerData.first_name || !this.registerData.last_name) {
      this.errorMessage = 'Por favor completa todos los campos obligatorios';
      return;
    }

    if (this.registerData.password !== this.confirmPassword) {
      this.errorMessage = 'Las contraseñas no coinciden';
      return;
    }

    if (this.registerData.password.length < 8) {
      this.errorMessage = 'La contraseña debe tener al menos 8 caracteres';
      return;
    }

    // Asignar password_confirm antes de enviar y forzar rol de estudiante
    this.registerData.password_confirm = this.confirmPassword;
    this.registerData.role = 'student'; // Siempre estudiante

    this.isLoading = true;
    this.errorMessage = '';
    this.successMessage = '';

    this.authService.register(this.registerData).subscribe({
      next: (response) => {
        this.successMessage = response.message || 'Registro exitoso';
        // Redirigir al dashboard después de un breve delay
        setTimeout(() => {
          this.router.navigate(['/']);
        }, 1500);
      },
      error: (error) => {
        this.isLoading = false;
        console.error('Error en registro:', error);
        
        if (error.error) {
          // Manejar errores específicos del backend
          if (error.error.username) {
            this.errorMessage = `Usuario: ${error.error.username[0]}`;
          } else if (error.error.email) {
            this.errorMessage = `Email: ${error.error.email[0]}`;
          } else if (error.error.first_name) {
            this.errorMessage = `Nombre: ${error.error.first_name[0]}`;
          } else if (error.error.last_name) {
            this.errorMessage = `Apellidos: ${error.error.last_name[0]}`;
          } else if (error.error.password) {
            this.errorMessage = `Contraseña: ${error.error.password[0]}`;
          } else if (error.error.error) {
            this.errorMessage = error.error.error;
          } else {
            this.errorMessage = 'Error en el registro. Intenta nuevamente.';
          }
        } else {
          this.errorMessage = 'Error en el registro. Intenta nuevamente.';
        }
      },
      complete: () => {
        this.isLoading = false;
      }
    });
  }

  goToLogin() {
    this.router.navigate(['/login']);
  }
  goToJournal() {
    this.router.navigate(['/']);
  }
}