import { Component, OnInit, ElementRef, ViewChild, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService, ChatMessage, ChatResponse } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-journal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './journal.component.html',
  styleUrls: ['./journal.component.scss']
})
export class JournalComponent implements OnInit, AfterViewChecked {
  messageText: string = '';
  isLoading: boolean = false;
  entries: any[] = []; // Mensajes del chat
  currentConversationId?: number;
  errorMessage: string = '';
  successMessage: string = '';
  
  @ViewChild('chatContainer') private chatContainer!: ElementRef;

  constructor(
    private apiService: ApiService, 
    private authService: AuthService,
    private router: Router
  ) {}

  ngOnInit() {
    // Verificar autenticación
    if (!this.authService.isAuthenticated()) {
      this.router.navigate(['/login']);
      return;
    }
    
    // Agregar mensaje de bienvenida inicial
    this.entries = [{
      type: 'ai',
      text: '¡Hola! Soy tu asistente de diario emocional. Puedes contarme cómo te sientes hoy, qué pensamientos tienes o cualquier cosa que quieras compartir. Estoy aquí para ayudarte.',
      timestamp: new Date(),
      isWelcome: true
    }];
    
    this.loadEntries();
  }

  ngAfterViewChecked() {
    this.scrollToBottom();
  }

  scrollToBottom(): void {
    try {
      this.chatContainer.nativeElement.scrollTop = this.chatContainer.nativeElement.scrollHeight;
    } catch(err) { }
  }

  sendMessage() {
    if (!this.messageText.trim() || this.isLoading) return;

    const userMessage = this.messageText;
    this.messageText = '';
    this.isLoading = true;
    this.errorMessage = '';
    this.successMessage = '';

    // Agregar mensaje de usuario inmediatamente
    this.entries.push({
      type: 'user',
      text: userMessage,
      timestamp: new Date(),
      isTemp: true // Marcar como temporal hasta tener respuesta
    });

    this.scrollToBottom();

    this.apiService.sendMessage({
      text: userMessage,
      conversation_id: this.currentConversationId
    }).subscribe({
      next: (response: ChatResponse) => {
        // Reemplazar el mensaje temporal con el real
        const tempIndex = this.entries.findIndex(entry => entry.isTemp);
        if (tempIndex !== -1) {
          this.entries.splice(tempIndex, 1);
        }

        // Actualizar el ID de la conversación para futuros mensajes
        this.currentConversationId = response.conversation_id;
        
        console.log(`📊 DEBUG: Nuevo mensaje enviado - Conversación ID: ${response.conversation_id}`);

        // Agregar mensaje del usuario a la interfaz
        this.entries.push({
          type: 'user',
          text: response.user_message_analysis.text,
          timestamp: new Date(),
          sentiment: response.user_message_analysis.sentiment,
          emotions: response.user_message_analysis.emotions,
          originalData: response
        });

        // Agregar respuesta del bot a la interfaz
        this.entries.push({
          type: 'ai',
          text: response.bot_response,
          timestamp: new Date(),
          originalData: response
        });
        
        console.log(`📊 DEBUG: Nuevas entradas agregadas. Total entradas actuales: ${this.entries.length}`);

        this.isLoading = false;
        this.successMessage = '¡Mensaje enviado!';
        
        setTimeout(() => {
          this.successMessage = '';
        }, 3000);
      },
      error: (error: any) => {
        console.error('Error enviando mensaje:', error);
        
        // Eliminar mensaje temporal en caso de error
        const tempIndex = this.entries.findIndex(entry => entry.isTemp);
        if (tempIndex !== -1) {
          this.entries.splice(tempIndex, 1);
        }
        
        this.errorMessage = 'Error al enviar el mensaje. Intenta nuevamente.';
        this.isLoading = false;
        this.messageText = userMessage; // Restaurar el mensaje
      }
    });
  }

  loadEntries() {
    this.apiService.getConversations().subscribe({
      next: (response: any) => {
        console.log('📊 DEBUG: Conversaciones obtenidas:', response);
        
        if (response.conversations && response.conversations.length > 0) {
          console.log(`📊 DEBUG: Total de conversaciones: ${response.conversations.length}`);
          
          // Cargar la conversación más reciente (primera en la lista ya viene ordenada por -start_time)
          const latestConversation = response.conversations[0];
          
          console.log(`📊 DEBUG: Conversación más reciente:`, {
            id: latestConversation.id,
            start_time: latestConversation.start_time,
            messages_count: latestConversation.messages_count,
            last_message: latestConversation.last_message
          });
          
          // Establecer la conversación actual
          this.currentConversationId = latestConversation.id;
          
          // Cargar todos los mensajes de la conversación más reciente
          this.loadConversationMessages(latestConversation.id);
        } else {
          // Si no hay conversaciones, limpiar la interfaz y preparar para nuevo chat
          console.log('📊 DEBUG: No hay conversaciones previas, iniciando nuevo chat');
          this.currentConversationId = undefined;
          // Mantener solo el mensaje de bienvenida
          this.entries = this.entries.filter(entry => entry.isWelcome);
        }
      },
      error: (error: any) => {
        console.error('Error cargando conversaciones:', error);
        this.errorMessage = 'Error al cargar el historial.';
      }
    });
  }

  loadConversationMessages(conversationId: number) {
    console.log(`📊 DEBUG: Cargando mensajes de conversación ID: ${conversationId}`);
    
    this.apiService.getConversationMessages(conversationId).subscribe({
      next: (response: any) => {
        console.log('📊 DEBUG: Respuesta completa de mensajes:', response);
        
        if (!response.messages || response.messages.length === 0) {
          console.log('📊 DEBUG: No hay mensajes en esta conversación');
          // Mantener solo el mensaje de bienvenida
          const welcomeMessage = this.entries.find((entry: any) => entry.isWelcome);
          this.entries = welcomeMessage ? [welcomeMessage] : [];
          return;
        }
        
        // Ordenar mensajes por timestamp para asegurar orden cronológico
        const sortedMessages = response.messages.sort((a: any, b: any) => 
          new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
        );
        
        const userMessages = sortedMessages.filter((msg: any) => msg.sender === 'user');
        const botMessages = sortedMessages.filter((msg: any) => msg.sender === 'bot');
        
        console.log(`📊 DEBUG: Total mensajes ordenados: ${sortedMessages.length}`);
        console.log(`📊 DEBUG: Mensajes de usuario: ${userMessages.length}`);
        console.log(`📊 DEBUG: Mensajes del bot: ${botMessages.length}`);
        
        // Convertir todos los mensajes a entradas de chat
        const chatEntries: any[] = [];
        sortedMessages.forEach((message: any, index: number) => {
          console.log(`📊 DEBUG: Procesando mensaje ${index + 1}:`, {
            id: message.id,
            sender: message.sender,
            text: message.text.substring(0, 50) + '...',
            timestamp: message.timestamp
          });
          
          chatEntries.push({
            type: message.sender === 'user' ? 'user' : 'ai',
            text: message.text,
            timestamp: new Date(message.timestamp),
            sentiment: message.analysis?.sentiment,
            emotions: message.analysis?.emotions,
            originalData: message
          });
        });
        
        console.log(`📊 DEBUG: Entradas de chat creadas: ${chatEntries.length}`);
        
        // Reemplazar el historial completo (manteniendo el mensaje de bienvenida al inicio)
        const welcomeMessage = this.entries.find((entry: any) => entry.isWelcome);
        this.entries = welcomeMessage ? [welcomeMessage, ...chatEntries] : chatEntries;
        
        console.log(`📊 DEBUG: Total entradas finales mostradas en interfaz: ${this.entries.length}`);
        console.log('📊 DEBUG: Estructura final de entradas:', this.entries.map((entry: any, idx: number) => ({
          index: idx,
          type: entry.type,
          isWelcome: entry.isWelcome,
          textPreview: entry.text ? entry.text.substring(0, 30) + '...' : 'N/A'
        })));
        
        // Scroll al final después de cargar el historial
        setTimeout(() => this.scrollToBottom(), 100);
      },
      error: (error: any) => {
        console.error('Error cargando mensajes:', error);
        this.errorMessage = 'Error al cargar los mensajes.';
      }
    });
  }

  formatTime(date: Date): string {
    return date.toLocaleTimeString('es-ES', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  }

  formatDate(date: Date): string {
    const today = new Date();
    const messageDate = new Date(date);
    
    if (messageDate.toDateString() === today.toDateString()) {
      return 'Hoy';
    }
    
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    
    if (messageDate.toDateString() === yesterday.toDateString()) {
      return 'Ayer';
    }
    
    return messageDate.toLocaleDateString('es-ES', {
      day: 'numeric',
      month: 'short'
    });
  }

  getSentimentColor(sentiment: string): string {
    switch (sentiment.toLowerCase()) {
      case 'pos': return '#4caf50'; // Verde
      case 'neg': return '#f44336'; // Rojo
      case 'neu': return '#ff9800'; // Naranja
      default: return '#9e9e9e'; // Gris
    }
  }

  getEmotionIcon(emotion: string): string {
    switch (emotion.toLowerCase()) {
      case 'joy': return '😊';
      case 'sadness': return '😢';
      case 'anger': return '😠';
      case 'fear': return '😨';
      case 'surprise': return '😲';
      case 'disgust': return '🤢';
      default: return '😐';
    }
  }

  logout() {
    this.authService.logout().subscribe({
      next: () => {
        console.log('Logout exitoso del servidor');
        this.router.navigate(['/login']);
      },
      error: (error: any) => {
        console.error('Error en logout del servidor, usando logout local:', error);
        // Si hay error en el backend, hacer logout local
        this.authService.logoutLocal();
        this.router.navigate(['/login']);
      }
    });
  }
}