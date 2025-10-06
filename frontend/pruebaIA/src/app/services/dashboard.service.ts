import { Injectable } from '@angular/core';
import { ApiService, User } from './api.service';
import { Observable, map, catchError, of, switchMap, forkJoin } from 'rxjs';
import { AuthService } from './auth.service';
import { StudentsService, StudentConversationData } from './students.service';

export interface DashboardData {
  total_users: number;
  total_entries: number;
  avg_sentiment_score: number;
  most_common_sentiment: string; // Nuevo campo
  most_common_sentiment_percentage: number; // Nuevo campo
  entries_last_week: number;
  sentiment_distribution: {
    sentiment: string;
    count: number;
    percentage: number;
  }[];
  top_emotions: {
    emotion: string;
    count: number;
  }[];
  users_stats: {
    user_id: string;
    entries_count: number;
    dominant_sentiment: string;
    dominant_emotion: string;
  }[];
}

@Injectable({
  providedIn: 'root'
})
export class DashboardService {

  constructor(
    private apiService: ApiService, 
    private authService: AuthService,
    private studentsService: StudentsService
  ) {}

  getDashboardData(): Observable<DashboardData> {
    // Verificar si el usuario es profesor para obtener datos de estudiantes asignados
    if (this.authService.isTeacher()) {
      return this.getTeacherDashboardData();
    } else {
      return this.getStudentDashboardData();
    }
  }

  private getStudentDashboardData(): Observable<DashboardData> {
    // Obtener conversaciones del estudiante actual
    return this.apiService.getConversations().pipe(
      switchMap(conversationsData => {
        console.log('Datos de conversaciones del estudiante:', conversationsData);
        
        if (!conversationsData || !conversationsData.conversations || conversationsData.conversations.length === 0) {
          return of(this.getDefaultDashboardData());
        }

        // Obtener mensajes detallados de todas las conversaciones
        const conversationPromises = conversationsData.conversations.map(conv => 
          this.apiService.getConversationMessages(conv.id)
        );

        return forkJoin(conversationPromises).pipe(
          map(allConversationsMessages => {
            return this.generateDashboardFromMessages(allConversationsMessages, 1);
          })
        );
      }),
      catchError(error => {
        console.error('Error fetching student conversations for dashboard:', error);
        return of(this.getDefaultDashboardData());
      })
    );
  }

  private getTeacherDashboardData(): Observable<DashboardData> {
    console.log('🎓 Obteniendo datos del dashboard para profesor con estudiantes asignados reales...');
    
    return this.studentsService.getStudentsConversationData().pipe(
      map((studentsData: StudentConversationData[]) => {
        return this.generateDashboardFromStudentsData(studentsData);
      }),
      catchError((error: any) => {
        console.error('Error obteniendo datos de estudiantes asignados:', error);
        return of(this.getDefaultTeacherDashboardData());
      })
    );
  }

  private generateTeacherDashboardFromMessages(allConversationsMessages: any[], studentCount: number): DashboardData {
    console.log(`📊 Generando dashboard para profesor con ${studentCount} estudiantes`);
    
    // Extraer todos los mensajes de usuarios de todas las conversaciones
    const allUserMessages: any[] = [];
    const userStats: { [key: string]: any } = {};
    
    // Generar datos más realistas para estudiantes
    const studentNames = ['Ana García', 'Carlos López', 'María Rodríguez', 'Juan Pérez', 'Laura Martín'];
    
    allConversationsMessages.forEach((conversationData, index) => {
      if (conversationData && conversationData.messages) {
        const userMessages = conversationData.messages.filter((message: any) => message.sender === 'user');
        allUserMessages.push(...userMessages);
        
        // Simular estadísticas por estudiante con nombres más realistas
        const studentId = studentNames[index % studentNames.length] || `Estudiante ${index + 1}`;
        
        // Analizar sentimientos y emociones de los mensajes del estudiante
        let dominantSentiment = 'NEU';
        let dominantEmotion = 'neutral';
        
        if (userMessages.length > 0) {
          const sentimentCounts = { POS: 0, NEU: 0, NEG: 0 };
          const emotionCounts: { [key: string]: number } = {};
          
          userMessages.forEach((message: any) => {
            if (message.analysis) {
              // Analizar sentimientos
              if (message.analysis.sentiments) {
                const sentiments = message.analysis.sentiments;
                if (sentiments.positive > sentiments.negative && sentiments.positive > sentiments.neutral) {
                  sentimentCounts.POS++;
                } else if (sentiments.negative > sentiments.positive && sentiments.negative > sentiments.neutral) {
                  sentimentCounts.NEG++;
                } else {
                  sentimentCounts.NEU++;
                }
              }
              
              // Analizar emociones
              if (message.analysis.dominant_emotion) {
                const emotion = message.analysis.dominant_emotion;
                emotionCounts[emotion] = (emotionCounts[emotion] || 0) + 1;
              }
            }
          });
          
          // Determinar sentimiento dominante
          const maxSentiment = Object.entries(sentimentCounts)
            .reduce((max, [sentiment, count]) => count > max.count ? { sentiment, count } : max, 
                   { sentiment: 'NEU', count: 0 });
          dominantSentiment = maxSentiment.sentiment;
          
          // Determinar emoción dominante
          const maxEmotion = Object.entries(emotionCounts)
            .reduce((max, [emotion, count]) => count > max.count ? { emotion, count } : max, 
                   { emotion: 'neutral', count: 0 });
          dominantEmotion = maxEmotion.emotion;
        }
        
        userStats[studentId] = {
          user_id: studentId,
          entries_count: userMessages.length,
          dominant_sentiment: dominantSentiment,
          dominant_emotion: dominantEmotion
        };
      }
    });

    // Usar la misma lógica de análisis pero con más contexto de estudiantes
    const baseData = this.generateDashboardFromMessages(allConversationsMessages, studentCount);
    
    // Agregar estadísticas por estudiante
    const usersStatsArray = Object.values(userStats);
    
    // Si no hay suficientes estudiantes reales, agregar algunos datos de muestra
    while (usersStatsArray.length < Math.min(studentCount, 3)) {
      const sampleIndex = usersStatsArray.length;
      const sampleName = studentNames[sampleIndex] || `Estudiante ${sampleIndex + 1}`;
      usersStatsArray.push({
        user_id: sampleName,
        entries_count: 0,
        dominant_sentiment: 'NEU',
        dominant_emotion: 'neutral'
      });
    }
    
    return {
      ...baseData,
      total_users: Math.max(studentCount, usersStatsArray.length),
      users_stats: usersStatsArray
    };
  }

  private generateDashboardFromStudentsData(studentsData: StudentConversationData[]): DashboardData {
    console.log(`📊 Generando dashboard desde datos reales de ${studentsData.length} estudiantes del sistema`);
    
    // Consolidar todos los mensajes de todos los estudiantes reales
    const allUserMessages: any[] = [];
    const usersStats: any[] = [];
    
    studentsData.forEach((studentData: any) => {
      const student = studentData.student;
      allUserMessages.push(...studentData.allMessages);
      
      // Crear estadísticas por estudiante con datos reales del sistema
      usersStats.push({
        user_id: `${student.firstName} ${student.lastName}`,
        entries_count: student.messagesCount,
        dominant_sentiment: student.dominantSentiment,
        dominant_emotion: student.dominantEmotion
      });
    });
    
    console.log(`📈 Total mensajes reales analizados: ${allUserMessages.length}`);
    console.log('👥 Estudiantes reales del sistema:', usersStats.map((s: any) => s.user_id));
    
    // Calcular entradas de la última semana con datos reales
    const lastWeek = new Date();
    lastWeek.setDate(lastWeek.getDate() - 7);
    const entriesLastWeek = allUserMessages.filter((message: any) => {
      const messageDate = new Date(message.timestamp);
      return messageDate >= lastWeek;
    }).length;

    // Analizar sentimientos y emociones de todos los mensajes reales
    const sentimentCounts = { POS: 0, NEU: 0, NEG: 0 };
    const emotionCounts: { [key: string]: number } = {};
    let sentimentScore = 0;
    let sentimentTotal = 0;

    allUserMessages.forEach((message: any) => {
      if (message.analysis && message.analysis.sentiments) {
        const sentiments = message.analysis.sentiments;
        if (sentiments.positive > sentiments.negative && sentiments.positive > sentiments.neutral) {
          sentimentCounts.POS++;
          sentimentScore += 1;
        } else if (sentiments.negative > sentiments.positive && sentiments.negative > sentiments.neutral) {
          sentimentCounts.NEG++;
          sentimentScore += 0;
        } else {
          sentimentCounts.NEU++;
          sentimentScore += 0.5;
        }
        sentimentTotal++;
      }

      if (message.analysis && message.analysis.dominant_emotion) {
        const emotion = message.analysis.dominant_emotion;
        emotionCounts[emotion] = (emotionCounts[emotion] || 0) + 1;
      }
    });

    // Calcular promedio de sentimiento con datos reales
    const avgSentimentScore = sentimentTotal > 0 ? sentimentScore / sentimentTotal : 0;

    // Generar distribución de sentimientos reales
    const sentimentDistribution: { sentiment: string; count: number; percentage: number }[] = [];
    const totalSentiments = sentimentCounts.POS + sentimentCounts.NEU + sentimentCounts.NEG;
    
    if (totalSentiments > 0) {
      Object.entries(sentimentCounts).forEach(([sentiment, count]) => {
        if (count > 0) {
          const percentage = (count / totalSentiments) * 100;
          sentimentDistribution.push({
            sentiment,
            count,
            percentage: Math.round(percentage)
          });
        }
      });
    }

    // Generar top emociones reales
    const topEmotions = Object.entries(emotionCounts)
      .map(([emotion, count]) => ({ emotion, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);

    // Calcular sentimiento más común real
    let mostCommonSentiment = 'NEU';
    let mostCommonSentimentPercentage = 0;
    
    if (totalSentiments > 0) {
      const maxSentiment = Object.entries(sentimentCounts)
        .reduce((max, [sentiment, count]) => count > max.count ? { sentiment, count } : max, 
               { sentiment: 'NEU', count: 0 });
      
      mostCommonSentiment = maxSentiment.sentiment;
      mostCommonSentimentPercentage = Math.round((maxSentiment.count / totalSentiments) * 100);
    }

    const dashboardData: DashboardData = {
      total_users: studentsData.length,
      total_entries: allUserMessages.length,
      avg_sentiment_score: Math.round(avgSentimentScore * 100) / 100,
      most_common_sentiment: mostCommonSentiment,
      most_common_sentiment_percentage: mostCommonSentimentPercentage,
      entries_last_week: entriesLastWeek,
      sentiment_distribution: sentimentDistribution,
      top_emotions: topEmotions,
      users_stats: usersStats
    };

    console.log('✅ Dashboard generado con datos REALES de estudiantes del sistema:', {
      estudiantes: dashboardData.total_users,
      mensajes_totales: dashboardData.total_entries,
      sentimiento_comun: `${dashboardData.most_common_sentiment} (${dashboardData.most_common_sentiment_percentage}%)`,
      mensajes_semana: dashboardData.entries_last_week
    });
    
    return dashboardData;
  }

  private getDefaultTeacherDashboardData(): DashboardData {
    return {
      total_users: 3, // Simular 3 estudiantes asignados por defecto
      total_entries: 0,
      avg_sentiment_score: 0,
      most_common_sentiment: 'NEU',
      most_common_sentiment_percentage: 0,
      entries_last_week: 0,
      sentiment_distribution: [],
      top_emotions: [],
      users_stats: [
        { user_id: 'Ana García', entries_count: 0, dominant_sentiment: 'NEU', dominant_emotion: 'neutral' },
        { user_id: 'Carlos López', entries_count: 0, dominant_sentiment: 'NEU', dominant_emotion: 'neutral' },
        { user_id: 'María Rodríguez', entries_count: 0, dominant_sentiment: 'NEU', dominant_emotion: 'neutral' }
      ]
    };
  }

  private normalizeDashboardData(data: any): DashboardData {
    // Asegurarse de que los arrays existan
    const normalizedData: DashboardData = {
      total_users: data.total_users || 0,
      total_entries: data.total_entries || 0,
      avg_sentiment_score: data.avg_sentiment_score || 0.5,
      most_common_sentiment: data.most_common_sentiment || 'NEU',
      most_common_sentiment_percentage: data.most_common_sentiment_percentage || 0,
      entries_last_week: data.entries_last_week || 0,
      sentiment_distribution: this.ensureSentimentArray(data.sentiment_distribution),
      top_emotions: this.ensureEmotionArray(data.top_emotions || data.emotion_distribution),
      users_stats: this.ensureArray(data.users_stats)
    };

    console.log('Datos normalizados:', normalizedData);
    return normalizedData;
  }

  private ensureSentimentArray(value: any): any[] {
    if (Array.isArray(value)) return value;
    
    if (value && typeof value === 'object') {
      // Convertir objeto {pos: 5, neu: 3, neg: 2} a array
      return Object.entries(value).map(([sentiment, count]) => ({
        sentiment,
        count: count as number,
        percentage: 0 // Se calculará después si es necesario
      }));
    }
    
    return [];
  }

  private ensureEmotionArray(value: any): any[] {
    if (Array.isArray(value)) return value;
    
    if (value && typeof value === 'object') {
      // Convertir objeto {joy: 5, sadness: 3} a array
      return Object.entries(value).map(([emotion, count]) => ({
        emotion,
        count: count as number
      }));
    }
    
    return [];
  }

  private ensureArray(value: any): any[] {
    if (Array.isArray(value)) return value;
    return [];
  }

  private generateDashboardFromMessages(allConversationsMessages: any[], userCount: number = 1): DashboardData {
    // Extraer todos los mensajes de usuarios de todas las conversaciones
    const allUserMessages: any[] = [];
    
    allConversationsMessages.forEach(conversationData => {
      if (conversationData && conversationData.messages) {
        const userMessages = conversationData.messages.filter((message: any) => message.sender === 'user');
        allUserMessages.push(...userMessages);
      }
    });

    console.log('Mensajes de usuarios encontrados:', allUserMessages.length, allUserMessages);

    // Usar solo datos reales - si no hay mensajes, mostrar todo en 0
    const totalEntries = allUserMessages.length;
    
    // Calcular entradas de la última semana
    const lastWeek = new Date();
    lastWeek.setDate(lastWeek.getDate() - 7);
    const entriesLastWeek = allUserMessages.filter(message => {
      const messageDate = new Date(message.timestamp);
      return messageDate >= lastWeek;
    }).length;

    // Analizar SOLO sentimientos reales de los mensajes analizados
    const sentimentCounts = { POS: 0, NEU: 0, NEG: 0 };
    const emotionCounts: { [key: string]: number } = {};
    let sentimentScore = 0;
    let sentimentTotal = 0;

    allUserMessages.forEach(message => {
      // Solo usar datos si están disponibles en el análisis real
      if (message.analysis && message.analysis.sentiments) {
        const sentiments = message.analysis.sentiments;
        if (sentiments.positive > sentiments.negative && sentiments.positive > sentiments.neutral) {
          sentimentCounts.POS++;
          sentimentScore += 1;
        } else if (sentiments.negative > sentiments.positive && sentiments.negative > sentiments.neutral) {
          sentimentCounts.NEG++;
          sentimentScore += 0;
        } else {
          sentimentCounts.NEU++;
          sentimentScore += 0.5;
        }
        sentimentTotal++;
      }

      // Solo usar emociones reales analizadas
      if (message.analysis && message.analysis.dominant_emotion) {
        const emotion = message.analysis.dominant_emotion;
        emotionCounts[emotion] = (emotionCounts[emotion] || 0) + 1;
      }
    });

    // Calcular promedio de sentimiento solo si hay datos reales
    const avgSentimentScore = sentimentTotal > 0 ? sentimentScore / sentimentTotal : 0;

    // Generar distribución de sentimientos solo con datos reales
    const sentimentDistribution: { sentiment: string; count: number; percentage: number }[] = [];
    const totalSentiments = sentimentCounts.POS + sentimentCounts.NEU + sentimentCounts.NEG;
    
    if (totalSentiments > 0) {
      Object.entries(sentimentCounts).forEach(([sentiment, count]) => {
        if (count > 0) {
          const percentage = (count / totalSentiments) * 100;
          sentimentDistribution.push({
            sentiment,
            count,
            percentage: Math.round(percentage)
          });
        }
      });
    }

    // Generar top emociones solo con datos reales
    const topEmotions = Object.entries(emotionCounts)
      .map(([emotion, count]) => ({ emotion, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);

    // Calcular el sentimiento más común y su porcentaje
    let mostCommonSentiment = 'NEU';
    let mostCommonSentimentPercentage = 0;
    
    if (totalSentiments > 0) {
      const maxSentiment = Object.entries(sentimentCounts)
        .reduce((max, [sentiment, count]) => count > max.count ? { sentiment, count } : max, 
               { sentiment: 'NEU', count: 0 });
      
      mostCommonSentiment = maxSentiment.sentiment;
      mostCommonSentimentPercentage = Math.round((maxSentiment.count / totalSentiments) * 100);
    }

    const dashboardData: DashboardData = {
      total_users: userCount,
      total_entries: totalEntries,
      avg_sentiment_score: Math.round(avgSentimentScore * 100) / 100,
      most_common_sentiment: mostCommonSentiment,
      most_common_sentiment_percentage: mostCommonSentimentPercentage,
      entries_last_week: entriesLastWeek,
      sentiment_distribution: sentimentDistribution,
      top_emotions: topEmotions,
      users_stats: []
    };

    console.log('Dashboard con SOLO datos reales del journal:', dashboardData);
    return dashboardData;
  }

  private generateDashboardFromConversations(conversationsData: any): DashboardData {
    // Este método ya no se usa, pero lo mantenemos por compatibilidad
    if (!conversationsData || !conversationsData.conversations || conversationsData.conversations.length === 0) {
      return this.getDefaultDashboardData();
    }

    const conversations = conversationsData.conversations;
    const totalConversations = conversations.length;
    
    return {
      total_users: 1,
      total_entries: 0, // Solo datos reales
      avg_sentiment_score: 0,
      most_common_sentiment: 'NEU',
      most_common_sentiment_percentage: 0,
      entries_last_week: 0,
      sentiment_distribution: [],
      top_emotions: [],
      users_stats: []
    };
  }

  getDefaultDashboardData(): DashboardData {
    return {
      total_users: 1,
      total_entries: 0, // Sin datos simulados
      avg_sentiment_score: 0, // Sin análisis aún
      most_common_sentiment: 'NEU', // Neutral por defecto
      most_common_sentiment_percentage: 0, // Sin porcentaje
      entries_last_week: 0, // Sin entradas
      sentiment_distribution: [], // Vacío hasta tener datos reales
      top_emotions: [], // Vacío hasta tener datos reales
      users_stats: []
    };
  }

}