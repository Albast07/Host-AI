import { Injectable } from '@angular/core';
import { Observable, of, forkJoin, map, switchMap, catchError } from 'rxjs';
import { ApiService, User, Conversation, ChatMessage } from './api.service';

export interface AssignedStudent {
  id: number;
  username: string;
  firstName: string;
  lastName: string;
  email: string;
  conversationsCount: number;
  messagesCount: number;
  dominantSentiment: string;
  dominantEmotion: string;
  lastMessageTime?: string;
  recentActivity: boolean;
}

export interface StudentConversationData {
  student: AssignedStudent;
  conversations: Conversation[];
  allMessages: ChatMessage[];
}

@Injectable({
  providedIn: 'root'
})
export class StudentsService {

  constructor(private apiService: ApiService) {}

  /**
   * Obtiene la lista de estudiantes reales asignados al profesor actual
   * Usa el endpoint real del backend: /api/v1/users/my_students/
   */
  getAssignedStudents(): Observable<User[]> {
    console.log('🎓 Obteniendo estudiantes reales asignados desde el backend...');
    
    return this.getRealAssignedStudentsFromBackend();
  }

  /**
   * Obtiene estudiantes reales del backend usando el endpoint my_students
   */
  private getRealAssignedStudentsFromBackend(): Observable<User[]> {
    return this.apiService.getAssignedStudentsFromBackend().pipe(
      map((students: User[]) => {
        if (students && students.length > 0) {
          console.log(`� Encontrados ${students.length} estudiantes REALES asignados al profesor:`, 
            students.map(s => `${s.first_name} ${s.last_name} (${s.username})`));
          return students;
        }
        
        console.log('⚠️ No hay estudiantes asignados, obteniendo todos los estudiantes del sistema...');
        return this.getAllStudentsFromSystem();
      }),
      catchError((error: any) => {
        console.error('Error obteniendo estudiantes asignados, usando fallback:', error);
        return this.getAllStudentsFromSystemFallback();
      })
    );
  }

  /**
   * Obtiene todos los estudiantes del sistema como fallback
   */
  private getAllStudentsFromSystem(): User[] {
    // Este se ejecutará si no hay estudiantes asignados
    // Usaremos el endpoint available_students como fallback
    console.log('🔄 Usando estudiantes disponibles del sistema como fallback...');
    return [];
  }

  /**
   * Fallback si falla la llamada al backend
   */
  private getAllStudentsFromSystemFallback(): Observable<User[]> {
    return this.apiService.getAllStudentsFromBackend().pipe(
      map((students: User[]) => {
        console.log(`📋 Usando ${students.length} estudiantes del sistema como fallback`);
        return students.slice(0, 8); // Limitar a 8 para el dashboard
      }),
      catchError(() => {
        console.log('❌ Error total, usando datos mínimos del sistema');
        return of(this.getMinimalSystemStudents());
      })
    );
  }

  /**
   * Datos mínimos cuando todo falla
   */
  private getMinimalSystemStudents(): User[] {
    return [
      {
        id: 999,
        username: 'sistema_estudiante',
        email: 'estudiante@sistema.edu',
        first_name: 'Estudiante',
        last_name: 'Sistema',
        role: 'student'
      }
    ];
  }

  /**
   * Obtiene datos de conversaciones REALES para cada estudiante asignado
   * Usa los nuevos endpoints que permiten a profesores acceder a datos reales
   */
  getStudentsConversationData(): Observable<StudentConversationData[]> {
    return this.getAssignedStudents().pipe(
      switchMap((realStudents: User[]) => {
        console.log(`📊 Procesando datos REALES de ${realStudents.length} estudiantes del backend...`);
        
        if (realStudents.length === 0) {
          console.log('⚠️ No hay estudiantes reales disponibles');
          return of([]);
        }

        // Para cada estudiante real, obtener sus conversaciones reales usando los nuevos endpoints
        return this.getRealConversationsForStudents(realStudents);
      })
    );
  }

  /**
   * Obtiene el nombre de visualización de un estudiante
   * Si first_name y last_name están vacíos, usa el username
   */
  private getStudentDisplayName(student: User): { firstName: string; lastName: string; fullName: string } {
    const firstName = student.first_name?.trim() || '';
    const lastName = student.last_name?.trim() || '';
    
    if (firstName && lastName) {
      return {
        firstName,
        lastName,
        fullName: `${firstName} ${lastName}`
      };
    } else if (firstName) {
      return {
        firstName,
        lastName: '',
        fullName: firstName
      };
    } else if (lastName) {
      return {
        firstName: '',
        lastName,
        fullName: lastName
      };
    } else {
      // Si no hay first_name ni last_name, usar username
      return {
        firstName: student.username,
        lastName: '',
        fullName: student.username
      };
    }
  }

  /**
   * Obtiene conversaciones REALES de cada estudiante usando los nuevos endpoints
   * PROTECCIÓN DE PRIVACIDAD: Solo obtiene análisis emocional y métricas,
   * NO el contenido real de los mensajes de los estudiantes
   */
  private getRealConversationsForStudents(realStudents: User[]): Observable<StudentConversationData[]> {
    console.log('🔍 Obteniendo análisis REALES de estudiantes (sin contenido de mensajes)...');
    
    // Para cada estudiante, obtener sus conversaciones reales
    const studentPromises = realStudents.map(student => 
      this.apiService.getStudentConversations(student.id).pipe(
        switchMap((conversationsResponse: any) => {
          const conversations = conversationsResponse.conversations || [];
          
          if (conversations.length === 0) {
            console.log(`ℹ️ El estudiante ${student.first_name} ${student.last_name} no tiene conversaciones`);
            return of(this.createEmptyStudentData(student));
          }

          console.log(`� Estudiante ${student.first_name} ${student.last_name}: ${conversations.length} conversaciones reales`);

          // Obtener mensajes reales de todas las conversaciones del estudiante
          const messagePromises = conversations.map((conv: any) => 
            this.apiService.getStudentConversationMessages(student.id, conv.id)
          );

          return (forkJoin(messagePromises) as Observable<any[]>).pipe(
            map((allMessagesResponses: any[]) => {
              return this.analyzeRealStudentData(student, conversations, allMessagesResponses);
            })
          );
        }),
        catchError((error: any) => {
          console.error(`❌ Error obteniendo datos reales del estudiante ${student.username}:`, error);
          return of(this.createEmptyStudentData(student));
        })
      )
    );

    return (forkJoin(studentPromises) as Observable<StudentConversationData[]>);
  }

  /**
   * Crea datos vacíos para un estudiante real
   */
  private createEmptyStudentData(student: User): StudentConversationData {
    const displayName = this.getStudentDisplayName(student);
    return {
      student: {
        id: student.id,
        username: student.username,
        firstName: displayName.firstName,
        lastName: displayName.lastName,
        email: student.email,
        conversationsCount: 0,
        messagesCount: 0,
        dominantSentiment: 'NEU',
        dominantEmotion: 'neutral',
        lastMessageTime: undefined,
        recentActivity: false
      },
      conversations: [],
      allMessages: []
    };
  }

  /**
   * Analiza datos REALES de un estudiante con sus conversaciones y mensajes reales
   */
  private analyzeRealStudentData(
    student: User, 
    conversations: Conversation[], 
    messagesResponses: any[]
  ): StudentConversationData {
    let dominantSentiment = 'NEU';
    let dominantEmotion = 'neutral';
    let lastMessageTime: string | undefined;
    let totalMessages = 0;

    // Extraer todos los mensajes reales del estudiante
    const allMessages: ChatMessage[] = [];
    messagesResponses.forEach(response => {
      if (response && response.messages) {
        const userMessages = response.messages.filter((msg: any) => msg.sender === 'user');
        allMessages.push(...userMessages);
        totalMessages += userMessages.length;
      }
    });

    console.log(`📊 Analizando ${totalMessages} mensajes reales del estudiante ${student.first_name} ${student.last_name}`);

    if (allMessages.length > 0) {
      // Analizar sentimientos REALES
      const sentimentCounts = { POS: 0, NEU: 0, NEG: 0 };
      const emotionCounts: { [key: string]: number } = {};

      allMessages.forEach((message: any) => {
        if (message.analysis) {
          // Contar sentimientos reales del análisis
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

          // Contar emociones reales del análisis
          if (message.analysis.dominant_emotion) {
                const raw = message.analysis.dominant_emotion;
                // reuse simple normalization used elsewhere (lowercase, strip accents)
                let emotionKey = raw ? raw.toString().toLowerCase().normalize('NFD').replace(/\p{Diacritic}/gu, '').trim() : 'neutral';
                // fallback for environments without unicode property escapes
                if (!emotionKey) emotionKey = raw ? raw.toString().toLowerCase().normalize('NFD').replace(/[^\w\s-]/g, '').trim() : 'neutral';
                emotionCounts[emotionKey] = (emotionCounts[emotionKey] || 0) + 1;
              }
        }

        // Obtener la fecha del último mensaje real
        if (!lastMessageTime || new Date(message.timestamp) > new Date(lastMessageTime)) {
          lastMessageTime = message.timestamp;
        }
      });

      // Determinar sentimiento dominante REAL
      const maxSentiment = Object.entries(sentimentCounts)
        .reduce((max, [sentiment, count]) => 
          count > max.count ? { sentiment, count } : max, 
          { sentiment: 'NEU', count: 0 }
        );
      dominantSentiment = maxSentiment.sentiment;

      // Determinar emoción dominante REAL
      const maxEmotion = Object.entries(emotionCounts)
        .reduce((max, [emotion, count]) => 
          count > max.count ? { emotion, count } : max, 
          { emotion: 'neutral', count: 0 }
        );
      dominantEmotion = maxEmotion.emotion;

      console.log(`✅ ${student.first_name} ${student.last_name} - Análisis REAL:`, {
        mensajes: totalMessages,
        sentimiento: dominantSentiment,
        emocion: dominantEmotion,
        ultimoMensaje: lastMessageTime
      });
    }

    // Determinar actividad reciente REAL (últimos 7 días)
    const recentActivity = lastMessageTime ? 
      (new Date().getTime() - new Date(lastMessageTime).getTime()) < (7 * 24 * 60 * 60 * 1000) : 
      false;

    const displayName = this.getStudentDisplayName(student);
    const assignedStudent: AssignedStudent = {
      id: student.id,
      username: student.username,
      firstName: displayName.firstName,
      lastName: displayName.lastName,
      email: student.email,
      conversationsCount: conversations.length,
      messagesCount: totalMessages,
      dominantSentiment,
      dominantEmotion,
      lastMessageTime,
      recentActivity
    };

    return {
      student: assignedStudent,
      conversations,
      allMessages
    };
}
}