// frontend/src/app/components/dashboard/dashboard.component.ts

import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService, DashboardData } from '../../services/api.service';
import { DashboardService } from '../../services/dashboard.service';
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
    , private dashboardService: DashboardService
  ) {}

  ngOnInit() {
    this.loadDashboardData();
    
    // Auto-refresh cada 30 segundos (30000 ms)
    // this.refreshSubscription = interval(30000).subscribe(() => {
    //   this.loadDashboardData();
    // });
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
        try {
          // Normalize/merge any duplicate emotion keys reported by the API
          this.dashboardData = this.dashboardService.normalizeDashboardData(data as any);
          try { console.log('🔎 DashboardComponent - dashboardData.top_emotions after normalize:', JSON.parse(JSON.stringify(this.dashboardData?.top_emotions))); } catch(e) { console.log('🔎 dashboardData.top_emotions', this.dashboardData?.top_emotions); }
        } catch (e) {
          // Fallback to raw data
          this.dashboardData = data;
        }
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
    const s = (sentiment || '').toString().toUpperCase();
    const emojis: { [key: string]: string } = {
      'POS': '😊',
      'NEG': '😔',
      'NEU': '😐'
    };
    return emojis[s] || '😐';
  }

  getSentimentLabel(sentiment: string): string {
    const s = (sentiment || '').toString().toUpperCase();
    const labels: { [key: string]: string } = {
      'POS': 'Positivo',
      'NEG': 'Negativo',
      'NEU': 'Neutral'
    };
    return labels[s] || 'Neutral';
  }

  getSentimentColor(sentiment: string): string {
    const s = (sentiment || '').toString().toUpperCase();
    const colors: { [key: string]: string } = {
      'POS': '#48bb78',
      'NEG': '#f56565',
      'NEU': '#a0aec0'
    };
    return colors[s] || '#a0aec0';
  }

  getEmotionIcon(emotion: string): string {
    const normalize = (s: string) => {
      if (!s) return '';
      // to lower, trim and remove accents
      return s.toString().toLowerCase().normalize('NFD').replace(/\p{Diacritic}/gu, '').trim();
    };
    const key = normalize(emotion);

    // map common english and spanish emotion labels to emojis
    const icons: { [key: string]: string } = {
      'joy': '😄', 'happy': '😄', 'alegria': '😄', 'alegría': '😄',
      'sadness': '😢', 'sad': '😢', 'tristeza': '😢',
      'anger': '😠', 'angry': '😠', 'ira': '😠', 'enojo': '😠',
      'fear': '😨', 'miedo': '😨',
      'disgust': '🤢', 'disgusted': '🤢', 'asco': '🤢',
      'surprise': '😲', 'sorpresa': '😲',
      'neutral': '😐', 'others': '😐', 'other': '😐'
    };

    return icons[key] || '😐';
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