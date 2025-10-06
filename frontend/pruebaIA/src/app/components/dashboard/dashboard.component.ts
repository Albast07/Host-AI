// frontend/src/app/components/dashboard/dashboard.component.ts

import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService, DashboardData } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';
import { Router } from '@angular/router';
import { interval, Subscription } from 'rxjs';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss']
})
export class DashboardComponent implements OnInit, OnDestroy {
  dashboardData: DashboardData | null = null;
  isLoading = false;
  errorMessage = '';
  private refreshSubscription?: Subscription;

  constructor(
    private apiService: ApiService,
    private authService: AuthService,
    private router: Router
  ) {}

  ngOnInit() {
    this.loadDashboardData();
    
    // Auto-refresh cada 30 segundos (30000 ms)
    this.refreshSubscription = interval(30000).subscribe(() => {
      this.loadDashboardData();
    });
  }

  ngOnDestroy() {
    // Limpiar la suscripción al destruir el componente
    if (this.refreshSubscription) {
      this.refreshSubscription.unsubscribe();
    }
  }

  loadDashboardData() {
    this.isLoading = true;
    this.errorMessage = '';

    this.apiService.getDashboardStats().subscribe({
      next: (data) => {
        this.dashboardData = data;
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error cargando dashboard:', error);
        this.errorMessage = 'Error al cargar los datos del dashboard';
        this.isLoading = false;
      }
    });
  }

  isTeacher(): boolean {
    return this.authService.isTeacher();
  }

  hasStudentData(): boolean {
    return !!(this.dashboardData && this.dashboardData.users_stats && this.dashboardData.users_stats.length > 0);
  }

  getDisplayName(student: any): string {
    return student.username || student.email || 'Usuario';
  }

  getSentimentEmoji(sentiment: string): string {
    const emojis: { [key: string]: string } = {
      'POS': '😊',
      'NEG': '😔',
      'NEU': '😐'
    };
    return emojis[sentiment] || '😐';
  }

  getSentimentLabel(sentiment: string): string {
    const labels: { [key: string]: string } = {
      'POS': 'Positivo',
      'NEG': 'Negativo',
      'NEU': 'Neutral'
    };
    return labels[sentiment] || 'Neutral';
  }

  getSentimentColor(sentiment: string): string {
    const colors: { [key: string]: string } = {
      'POS': '#48bb78',
      'NEG': '#f56565',
      'NEU': '#a0aec0'
    };
    return colors[sentiment] || '#a0aec0';
  }

  getEmotionIcon(emotion: string): string {
    const icons: { [key: string]: string } = {
      'joy': '😄',
      'sadness': '😢',
      'anger': '😠',
      'fear': '😨',
      'disgust': '🤢',
      'surprise': '😲',
      'others': '😐'
    };
    return icons[emotion] || '😐';
  }

  logout() {
    this.authService.logout().subscribe({
      next: () => {
        this.router.navigate(['/login']);
      },
      error: () => {
        this.authService.logoutLocal();
        this.router.navigate(['/login']);
      }
    });
  }
}