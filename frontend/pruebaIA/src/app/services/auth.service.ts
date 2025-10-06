import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, BehaviorSubject } from 'rxjs';
import { tap } from 'rxjs/operators';
import { environment } from '../../environments/environment.prod';

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  password_confirm: string;
  first_name?: string;
  last_name?: string;
  role?: string;
  fecha_de_nacimiento: string;
}

export interface AuthResponse {
  user: any;
  token: string;
  message: string;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private baseUrl = `${environment.apiUrl}/users`;
  private tokenKey = 'auth_token';
  private currentUserSubject = new BehaviorSubject<any>(null);
  public currentUser$ = this.currentUserSubject.asObservable();

  constructor(private http: HttpClient) {
    // Verificar si hay token al inicializar el servicio
    const token = this.getToken();
    if (token) {
      // Opcionalmente, verificar si el token es válido
      this.loadCurrentUser();
    }
  }

  register(userData: RegisterRequest): Observable<AuthResponse> {
    console.log('Datos enviados al registro:', userData); // Debug temporal
    return this.http.post<AuthResponse>(`${this.baseUrl}/register/`, userData)
      .pipe(
        tap(response => {
          if (response.token) {
            this.setToken(response.token);
            this.currentUserSubject.next(response.user);
          }
        })
      );
  }

  login(credentials: LoginRequest): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${this.baseUrl}/login/`, credentials)
      .pipe(
        tap(response => {
          if (response.token) {
            this.setToken(response.token);
            this.currentUserSubject.next(response.user);
          }
        })
      );
  }

  logout(): Observable<any> {
    const headers = this.getAuthHeaders();
    return this.http.post(`${this.baseUrl}/logout/`, {}, { headers })
      .pipe(
        tap(() => {
          this.removeToken();
          this.currentUserSubject.next(null);
        })
      );
  }

  getToken(): string | null {
    return localStorage.getItem(this.tokenKey);
  }

  setToken(token: string): void {
    localStorage.setItem(this.tokenKey, token);
  }

  removeToken(): void {
    localStorage.removeItem(this.tokenKey);
    this.currentUserSubject.next(null);
  }

  // Logout local sin petición al backend
  logoutLocal(): void {
    this.removeToken();
  }

  isAuthenticated(): boolean {
    return !!this.getToken();
  }

  getAuthHeaders(): HttpHeaders {
    const token = this.getToken();
    if (token) {
      return new HttpHeaders({
        'Authorization': `Token ${token}`,
        'Content-Type': 'application/json'
      });
    }
    return new HttpHeaders({
      'Content-Type': 'application/json'
    });
  }

  getCurrentUser(): any {
    return this.currentUserSubject.value;
  }

  isStudent(): boolean {
    const user = this.getCurrentUser();
    return user && user.role === 'student';
  }

  isTeacher(): boolean {
    const user = this.getCurrentUser();
    return user && user.role === 'teacher';
  }

  private loadCurrentUser(): void {
    // Obtener información del usuario actual si hay token
    this.http.get(`${this.baseUrl}/profile/`, { 
      headers: this.getAuthHeaders() 
    }).subscribe({
      next: (user) => {
        this.currentUserSubject.next(user);
      },
      error: () => {
        // Si hay error, el token probablemente es inválido
        this.removeToken();
      }
    });
  }

  // Método de conveniencia para hacer login automático como estudiante
  autoLoginAsStudent(): Observable<AuthResponse> {
    const studentCredentials = {
      username: 'estudiante_demo',
      password: 'demo123'
    };
    
    return this.login(studentCredentials);
  }
}