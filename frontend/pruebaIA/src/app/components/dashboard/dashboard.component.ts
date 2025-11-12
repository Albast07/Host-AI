// frontend/src/app/components/dashboard/dashboard.component.ts

import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, DashboardData } from '../../services/api.service';
import { DashboardService } from '../../services/dashboard.service';
import { AuthService } from '../../services/auth.service';
import { Router } from '@angular/router';
import { interval, Subscription } from 'rxjs';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss']
})
export class DashboardComponent implements OnInit, OnDestroy {
  dashboardData: DashboardData | null = null;
  // Cursos y recomendaciones
  courses: any[] = [];
  selectedCourseId: number | null = null;
  courseRecommendations: any[] = [];
  isRequestingRecommendation = false;
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
    if (this.isTeacher()) {
      this.loadCourses();
    }
    
    // Auto-refresh cada 30 segundos (30000 ms)
    // this.refreshSubscription = interval(30000).subscribe(() => {
    //   this.loadDashboardData();
    // });
  }

  loadCourses() {
    this.apiService.getCourses().subscribe({
      next: (courses: any[]) => {
        this.courses = courses || [];
        // Select the first course by default
        if (this.courses.length > 0) {
          this.selectedCourseId = this.courses[0].id;
          this.loadCourseRecommendations(this.selectedCourseId!);
        }
      },
      error: (err: any) => {
        console.error('Error cargando cursos:', err);
      }
    });
  }

  loadCourseRecommendations(courseId: number | null) {
    if (courseId == null) return;
    this.courseRecommendations = [];
    this.apiService.getCourseRecommendations(courseId).subscribe({
      next: (data: any) => {
        // API may return either:
        // - an array of recommendation objects, or
        // - an object with shape { course: {...}, results: [...] }
        // Normalize to an array of recommendation objects for the template.
        if (Array.isArray(data)) {
          this.courseRecommendations = data;
        } else if (data) {
          if (data.results && Array.isArray(data.results)) {
            this.courseRecommendations = data.results;
          } else {
            // Fallback: wrap single recommendation-like object
            this.courseRecommendations = [data];
          }
        }
      },
      error: (err: any) => {
        console.error('Error cargando recomendaciones del curso:', err);
      }
    });
  }

  requestRecommendation() {
    if (!this.selectedCourseId || this.isRequestingRecommendation) return;
    console.log('requestRecommendation() selectedCourseId=', this.selectedCourseId);
    this.isRequestingRecommendation = true;
    const courseIdNum = Number(this.selectedCourseId);
    if (!courseIdNum || Number.isNaN(courseIdNum)) {
      alert('Selecciona un curso válido antes de solicitar una sugerencia.');
      this.isRequestingRecommendation = false;
      return;
    }
    this.apiService.requestCourseRecommendation(courseIdNum).subscribe({
      next: (rec: any) => {
        // prepend new recommendation
        if (rec) this.courseRecommendations.unshift(rec);
        this.isRequestingRecommendation = false;
      },
      error: (err: any) => {
        console.error('Error al solicitar recomendación:', err);
        const message = (err && err.error && (err.error.detail || err.error.error)) || err?.message || ('HTTP ' + err?.status) || 'Error al solicitar recomendación';
        alert('Error al solicitar recomendación: ' + message);
        this.isRequestingRecommendation = false;
      }
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
      next: (data: any) => {
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
      error: (error: any) => {
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

  exportPdf() {
    if (!this.isTeacher()) return;

    this.apiService.exportDashboardPdf().subscribe({
      next: (blob: Blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        // Suggest filename from server or fallback
        const suggested = `reporte_emocional_${new Date().toISOString().slice(0,19).replace(/[:T]/g,'_')}.pdf`;
        a.download = suggested;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      },
      error: (err: any) => {
        console.error('Error exporting PDF:', err);
        // If server returned a JSON body but as a Blob (application/json), read it and show the message
        if (err && err.error && typeof err.error === 'object' && typeof err.error.text === 'function') {
          err.error.text().then((txt: string) => {
            let parsed: any = null;
            try { parsed = JSON.parse(txt); } catch (e) { parsed = null; }
            const serverMsg = parsed?.detail || parsed?.error || txt || `HTTP ${err.status}`;
            alert('Error al exportar el PDF: ' + serverMsg);
          }).catch(() => {
            alert('Error al exportar el PDF. Revisa la consola para más detalles.');
          });
        } else {
          const message = (err && err.error && (err.error.detail || err.error.error)) || err?.message || ('HTTP ' + err?.status) || 'Error al exportar el PDF';
          alert('Error al exportar el PDF: ' + message);
        }
      }
    });
  }
}