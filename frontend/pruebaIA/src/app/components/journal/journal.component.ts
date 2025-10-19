import { Component, OnInit, ElementRef, ViewChild, AfterViewChecked } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { OnboardingComponent } from '../onboarding/onboarding.component';
import { Router } from '@angular/router';
import { take } from 'rxjs/operators';
import { ApiService, ChatMessage, ChatResponse } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-journal',
  standalone: true,
  imports: [CommonModule, FormsModule, OnboardingComponent],
  templateUrl: './journal.component.html',
  styleUrls: ['./journal.component.scss']
})
export class JournalComponent implements OnInit, AfterViewChecked {
  showOnboarding = false;
  messageText: string = '';
  isLoading: boolean = false;
  entries: any[] = [];
  currentConversationId?: any;
  errorMessage: string = '';
  successMessage: string = '';
  conversations: any[] = [];
  selectedConversationId?: any;
  // allow string keys for local temporary ids
  journalNames: { [id: string]: string } = {};
  newJournalName: string = '';
  showNewForm: boolean = false;
  // track local temporary conversation ids (strings) created client-side
  localTempIds: string[] = [];
  renamingId: any | null = null;
  renameValue: string = '';
  @ViewChild('chatContainer') private chatContainer!: ElementRef;

  constructor(
    private apiService: ApiService, 
    private authService: AuthService,
    private router: Router
  ) {}

  ngOnInit() {
    if (!this.authService.isAuthenticated()) {
      this.router.navigate(['/login']);
      return;
    }
    this.entries = [{
      type: 'ai',
      text: '¡Hola! Soy tu asistente de diario emocional. Puedes contarme cómo te sientes hoy, qué pensamientos tienes o cualquier cosa que quieras compartir. Estoy aquí para ayudarte.',
      timestamp: new Date(),
      isWelcome: true
    }];
    this.loadConversations();
    // Show onboarding once per student (persisted by user id)
    try {
      const currentUser = this.authService.getCurrentUser();
      if (currentUser && currentUser.role === 'student') {
        const seenKey = `onboarding_shown_${currentUser.id}`;
        const shown = localStorage.getItem(seenKey);
        if (!shown) {
          setTimeout(() => this.showOnboarding = true, 200);
        }
      }
    } catch (e) {
      // ignore if current user not ready yet
    }

    // Fallback: if user wasn't ready synchronously, listen once for currentUser to load
    if (!this.showOnboarding) {
      this.authService.currentUser$.pipe(take(1)).subscribe((user: any) => {
        try {
          if (user && user.role === 'student') {
            const seenKey = `onboarding_shown_${user.id}`;
            const shown = localStorage.getItem(seenKey);
            if (!shown) {
              setTimeout(() => this.showOnboarding = true, 200);
            }
          }
        } catch (e) {
          // ignore
        }
      });
    }
  }

  onOnboardingClose() {
    try {
      const currentUser = this.authService.getCurrentUser();
      if (currentUser && currentUser.id) {
        const seenKey = `onboarding_shown_${currentUser.id}`;
        localStorage.setItem(seenKey, '1');
      } else {
        // fallback to a generic key for anonymous/browser-only persistence
        localStorage.setItem('onboarding_shown_guest', '1');
      }
    } catch (e) {
      localStorage.setItem('onboarding_shown_guest', '1');
    }
    this.showOnboarding = false;
  }

  openOnboarding() {
    this.showOnboarding = true;
  }
// ...resto del código sin cambios...

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
  const isLocalTemp = typeof this.currentConversationId === 'string' && String(this.currentConversationId).startsWith('local-');
  const tempSelectedId = isLocalTemp ? String(this.currentConversationId) : undefined;
  const payload: any = { text: userMessage };
  if (!isLocalTemp) payload.conversation_id = this.currentConversationId;

  this.apiService.sendMessage(payload).subscribe({
      next: (response: ChatResponse) => {
        // Reemplazar el mensaje temporal con el real
        const tempIndex = this.entries.findIndex(entry => entry.isTemp);
        if (tempIndex !== -1) {
          this.entries.splice(tempIndex, 1);
        }
        // Actualizar el ID de la conversación para futuros mensajes
        this.currentConversationId = response.conversation_id;

        console.log(`📊 DEBUG: Nuevo mensaje enviado - Conversación ID: ${response.conversation_id}`);

        // If this was a local temporary conversation, migrate its metadata (name)
        // to the server-provided conversation id and remove the temp marker.
        if (isLocalTemp && tempSelectedId) {
          if (this.journalNames[tempSelectedId]) {
            this.journalNames[String(response.conversation_id)] = this.journalNames[tempSelectedId];
            delete this.journalNames[tempSelectedId];
          }
          // remove temp id from tracking
          this.localTempIds = this.localTempIds.filter(id => id !== tempSelectedId);
          // Persist names
          localStorage.setItem('journalNames', JSON.stringify(this.journalNames));

          // Ensure UI selection points to the new server conversation id
          this.selectedConversationId = response.conversation_id;
          this.currentConversationId = response.conversation_id;

          // Reload conversations to show the new server conversation in the list
          this.loadConversations();
        }

        // Agregar mensaje del usuario a la interfaz (con análisis devuelto)
        if (response.user_message_analysis) {
          this.entries.push({
            type: 'user',
            text: response.user_message_analysis.text,
            timestamp: new Date(),
            sentiment: response.user_message_analysis.sentiment,
            emotions: response.user_message_analysis.emotions,
            originalData: response
          });
        }

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

  loadConversations() {
    this.apiService.getConversations().subscribe({
      next: (response: any) => {
  const serverConvs = response.conversations || [];
  // Ensure we have the latest local journal names before building the list
  this.loadJournalNames();
  // Map local temp conversations to the same shape so the UI shows them
  const localConvs = this.localTempIds.map(id => ({ id, title: this.getJournalName(id), isLocal: true }));
  // Prefer server-side conversations first so persisted messages (including bot replies)
  // are shown by default — local temporary journals should not override the default selection.
  this.conversations = [...serverConvs, ...localConvs];
        if (this.conversations.length > 0) {
          // If there is no previously selected conversation or the selection is no longer present,
          // choose a server conversation by default (so stored history appears). If no server
          // conversations exist, fall back to the first local conversation.
          const selectionMissing = !this.selectedConversationId || !this.conversations.some(c => String(c.id) === String(this.selectedConversationId));
          if (selectionMissing) {
            const defaultConv = this.conversations.find(c => !c.isLocal) || this.conversations[0];
            if (defaultConv) this.selectConversation(defaultConv.id);
          }
        } else {
          this.selectedConversationId = undefined;
          this.currentConversationId = undefined;
          this.entries = this.entries.filter(entry => entry.isWelcome);
        }
      },
      error: (error: any) => {
        this.errorMessage = 'Error al cargar el historial.';
      }
    });
  }

  selectConversation(conversationId: any) {
    this.selectedConversationId = conversationId;
    this.currentConversationId = conversationId;
    // If it's a local temp conversation, don't call the backend for messages yet
    if (typeof conversationId === 'string' && String(conversationId).startsWith('local-')) {
      const welcomeMessage = this.entries.find((entry: any) => entry.isWelcome);
      this.entries = welcomeMessage ? [welcomeMessage] : [];
      return;
    }
    this.loadConversationMessages(conversationId);
  }

  createNewJournal() {
    // Create a local temporary conversation id and select it without calling the backend.
    const tempId = `local-${Date.now()}`;
  this.localTempIds.push(tempId);
    this.currentConversationId = tempId as any;
    this.selectedConversationId = tempId as any;

    // Save the custom name locally (will be migrated to server id after first message)
    if (this.newJournalName.trim()) {
      this.saveJournalName(tempId as any, this.newJournalName.trim());
    }

    // Add the temporary conversation to the UI list immediately (no backend call)
    const localConv = { id: tempId, title: this.getJournalName(tempId), isLocal: true };
    this.conversations = [localConv, ...this.conversations];

    this.newJournalName = '';
    this.showNewForm = false;
  }

  openNewJournalForm() {
    this.showNewForm = true;
  }

  cancelNewJournalForm() {
    this.showNewForm = false;
    this.newJournalName = '';
  }

  startRenaming(id: any) {
    this.renamingId = id;
    this.renameValue = this.getJournalName(id);
  }

  saveRename(id: any) {
    const defaultName = this.getJournalName(id);
    this.saveJournalName(id, this.renameValue.trim() || defaultName);
    this.renamingId = null;
    this.renameValue = '';
  }

  cancelRename() {
    this.renamingId = null;
    this.renameValue = '';
  }

  // --- LocalStorage para nombres personalizados ---
  loadJournalNames() {
    const stored = localStorage.getItem('journalNames');
    this.journalNames = stored ? JSON.parse(stored) : {};
  }
  saveJournalName(id: any, name: string) {
    this.journalNames[String(id)] = name;
    localStorage.setItem('journalNames', JSON.stringify(this.journalNames));
  }
  getJournalName(id: any): string {
    const key = String(id);
    // Return custom name if the user set one
    if (this.journalNames[key]) return this.journalNames[key];

    // Compute a per-user index based on the current conversations array (includes local temps)
    const idx = this.conversations.findIndex(conv => String(conv.id) === key);
    if (idx !== -1) {
      return `Diario #${idx + 1}`;
    }

    // Fallback: if not found in current list, return a generic label
    return `Diario`;
  }

  loadConversationMessages(conversationId: any) {
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
        
        // Convertir todos los mensajes a entradas de chat (skipping initial placeholder messages)
        const chatEntries: any[] = [];
            sortedMessages.forEach((message: any, index: number) => {
              console.log(`📊 DEBUG: Procesando mensaje ${index + 1}:`, {
                id: message.id,
                sender: message.sender,
                text: message.text ? message.text.substring(0, 50) + '...' : '',
                timestamp: message.timestamp
              });

              // Known exact user-start placeholders we want to ignore when present in server data.
              const exactUserPlaceholders = [
                'Inicio de nuevo journal',
                'Inicio de nuevo diario',
                'Inicio de nuevo Journal',
                'Inicio de nuevo Diario'
              ];
              // Skip only exact known user placeholder messages used to create new journals.
              if (message.sender === 'user' && exactUserPlaceholders.includes(message.text?.trim())) {
                return;
              }
              // Do NOT broadly skip assistant messages. If the server stored an assistant reply it
              // should be shown. Only skip assistant messages if they exactly match a known
              // development-simulated string (rare). Keep the check strict.
              const assistantDevPlaceholders = ['Respuesta simulada', 'Simulada', 'Modo desarrollo'];
              if (message.sender === 'bot' && assistantDevPlaceholders.includes(message.text?.trim())) {
                return;
              }

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