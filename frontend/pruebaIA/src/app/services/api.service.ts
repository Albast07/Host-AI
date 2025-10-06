// frontend/src/app/services/api.service.ts

import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AuthService } from './auth.service';

export interface ChatMessage {
  id: number;
  text: string;
  sender: 'user' | 'bot';
  timestamp: string;
  analysis?: {
    dominant_emotion: string;
    sentiment: string;
    emotions: any;
    sentiments: any;
  };
}

export interface ChatResponse {
  bot_response: string;
  conversation_id: number;
  emotional_insight: {
    primary_emotion: string;
    intensity: string;
    educational_tip: string;
  };
  user_message_analysis: {
    text: string;
    sentiment: any;
    emotions: any;
  };
}

export interface Conversation {
  id: number;
  start_time: string;
  messages_count: number;
  last_message: string;
  last_message_time: string;
}

export interface CreateMessageRequest {
  text: string;
  conversation_id?: number;
}

export interface User {
  id: number;
  username: string;
  email: string;
  role: 'student' | 'teacher';
  fecha_de_nacimiento?: string;
  date_joined?: string;
}

// NUEVA INTERFAZ - AGREGAR ESTO
export interface DashboardData {
  total_users: number;
  total_entries: number;
  most_common_sentiment: string;
  most_common_sentiment_percentage: number;
  entries_last_week: number;
  sentiment_distribution: Array<{
    sentiment: string;
    count: number;
    percentage: number;
  }>;
  top_emotions: Array<{
    emotion: string;
    count: number;
  }>;
  users_stats: Array<{
    user_id: number;
    username: string;
    email: string;
    entries_count: number;
    dominant_sentiment: string;
    dominant_emotion: string;
  }>;
}

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private baseUrl = '/api/v1';

  constructor(private http: HttpClient, private authService: AuthService) {}

  // ========== MÉTODOS PARA CHAT (SOLO ESTUDIANTES) ==========
  
  sendMessage(message: CreateMessageRequest): Observable<ChatResponse> {
    return this.http.post<ChatResponse>(`${this.baseUrl}/chat/`, message, {
      headers: this.authService.getAuthHeaders()
    });
  }

  getConversations(): Observable<{conversations: Conversation[]}> {
    return this.http.get<{conversations: Conversation[]}>(`${this.baseUrl}/chat/`, {
      headers: this.authService.getAuthHeaders()
    });
  }

  getConversationMessages(conversationId: number): Observable<{
    conversation_id: number, 
    start_time: string, 
    messages: ChatMessage[]
  }> {
    return this.http.get<{
      conversation_id: number, 
      start_time: string, 
      messages: ChatMessage[]
    }>(`${this.baseUrl}/chat/?conversation_id=${conversationId}`, {
      headers: this.authService.getAuthHeaders()
    });
  }

  // ========== MÉTODOS PARA USUARIOS ==========
  
  getCurrentUser(): Observable<User> {
    return this.http.get<User>(`${this.baseUrl}/users/profile/`, {
      headers: this.authService.getAuthHeaders()
    });
  }

  // ========== MÉTODOS PARA PROFESORES ==========
  
  getAssignedStudents(): Observable<User[]> {
    return this.http.get<User[]>(`${this.baseUrl}/users/my_students/`, {
      headers: this.authService.getAuthHeaders()
    });
  }

  getAllStudents(): Observable<User[]> {
    return this.http.get<User[]>(`${this.baseUrl}/users/available_students/`, {
      headers: this.authService.getAuthHeaders()
    });
  }

  assignStudent(studentId: number): Observable<{message: string}> {
    return this.http.post<{message: string}>(`${this.baseUrl}/users/assign_student/`, 
      { student_id: studentId },
      { headers: this.authService.getAuthHeaders() }
    );
  }

  // ========== MÉTODO PARA DASHBOARD - AGREGAR ESTO ==========
  
  getDashboardStats(): Observable<DashboardData> {
    return this.http.get<DashboardData>(`${this.baseUrl}/chat/dashboard/`, {
      headers: this.authService.getAuthHeaders()
    });
  }
}