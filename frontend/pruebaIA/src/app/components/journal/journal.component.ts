import { Component, OnInit, ElementRef, ViewChild, AfterViewChecked, OnDestroy } from '@angular/core';
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
  showAssistant: boolean = false;
  suggestions: string[] = [];
  showMobileJournals: boolean = false;
  showMobileCreateModal: boolean = false;
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

  // Función para limpiar el texto de comillas y asteriscos
  cleanMessageText(text: string): string {
    if (!text) return text;
    
    return text
      // Eliminar asteriscos usados para énfasis
      .replace(/\*/g, '')
      // Eliminar comillas dobles innecesarias
      .replace(/"/g, '')
      // Limpiar espacios múltiples que puedan quedar
      .replace(/\s+/g, ' ')
      .trim();
  }

  ngOnInit() {
    // Add a body class so global styles can hide the page scrollbar on mobile
    try { document.body.classList.add('journal-fullscreen'); } catch(e) {}
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

  ngOnDestroy() {
    try { document.body.classList.remove('journal-fullscreen'); } catch(e) {}
  }

  toggleAssistant(): void {
    this.showAssistant = !this.showAssistant;
    if (this.showAssistant && (!this.suggestions || this.suggestions.length === 0)) {
      this.computeAssistantSuggestions();
    }
  }

  toggleMobileJournals(): void {
    this.showMobileJournals = !this.showMobileJournals;
    // If opening, ensure the chat input doesn't accidentally keep focus
    if (this.showMobileJournals) {
      try { (document.activeElement as HTMLElement)?.blur(); } catch(e) {}
    }
  }

  openMobileCreate(): void {
    this.showMobileCreateModal = true;
    // blur any focused element to avoid mobile keyboard oddities until user taps input
    try { (document.activeElement as HTMLElement)?.blur(); } catch(e) {}
  }

  closeMobileCreate(): void {
    this.showMobileCreateModal = false;
    this.newJournalName = '';
  }

  computeAssistantSuggestions(): void {
    const tipsSet = new Set<string>();

    // 1) Prefer explicit backend tips included in the immediate chat response
    for (const entry of this.entries) {
      if (!entry || !entry.originalData) continue;

      try {
        const ei = entry.originalData.emotional_insight;
        if (ei && ei.educational_tip && ei.educational_tip.toString().trim()) {
          tipsSet.add(ei.educational_tip.toString().trim());
        }
      } catch (e) { /* ignore */ }

      try {
        const sr = entry.originalData.support_resources;
        // support_resources follows serializer: { available, message, educational_insight, techniques }
        if (sr && sr.available) {
          if (sr.message && sr.message.toString().trim()) {
            tipsSet.add(sr.message.toString().trim());
          }
          // Add each technique title as a concise suggestion
          if (Array.isArray(sr.techniques)) {
            sr.techniques.forEach((t: any) => {
              if (t && t.title) tipsSet.add(`${t.title}: ${Array.isArray(t.steps) ? t.steps[0] : ''}`);
            });
          }
        }
      } catch (e) { /* ignore */ }
    }

    // 2) If still empty, synthesize suggestions from recent message analyses stored in the entries
    if (tipsSet.size === 0) {
      // Look at the last N entries for sentiment/emotion cues
      const N = Math.min(8, this.entries.length);
      const recent = this.entries.slice(-N);
      let negCount = 0;
      const emotionCounts: { [k: string]: number } = {};

      recent.forEach(e => {
        // try multiple possible shapes: e.sentiment, e.analysis, e.originalData.user_message_analysis
        try {
          const sent = e?.sentiment || e?.analysis?.sentiment || e?.originalData?.user_message_analysis?.sentiment?.dominant || e?.originalData?.user_message_analysis?.sentiment?.label;
          if (sent && typeof sent === 'string' && /neg/i.test(sent)) negCount++;
        } catch (err) {}

        try {
          const emo = e?.emotions?.label || e?.analysis?.dominant_emotion || e?.originalData?.user_message_analysis?.emotions_primary?.dominant || e?.originalData?.emotional_insight?.primary_emotion;
          if (emo && typeof emo === 'string') {
            const key = emo.toLowerCase().normalize('NFD').replace(/\p{Diacritic}/gu, '').split(' ')[0];
            emotionCounts[key] = (emotionCounts[key] || 0) + 1;
          }
        } catch (err) {}
      });

      // If many negatives, suggest grounding + breathing
      if (negCount >= Math.max(2, Math.floor(N / 3))) {
        tipsSet.add('Sugerencia: Parece haber un tono negativo persistente — prueba una técnica corta de regulación: Respiración 4‑7‑8 (2–3 min) y la técnica 5‑4‑3‑2‑1 para anclar al presente.');
      }

      // If a dominant emotion is present, tailor a suggestion
      const dominant = Object.entries(emotionCounts).sort((a,b) => b[1]-a[1])[0];
      if (dominant && dominant[0]) {
        const emo = dominant[0];
        if (/trist|sad|triste/.test(emo)) {
          tipsSet.add('Sugerencia: Para tristeza, sugiere respirar y hacer un ejercicio de journaling breve: escribe cómo te sientes en 5 frases.');
        } else if (/mied|fear/.test(emo)) {
          tipsSet.add('Sugerencia: Para miedo/ansiedad, identifica un paso pequeño (5 minutos) que puedas hacer ahora para reducir la incertidumbre.');
        } else if (/enojo|ira|anger/.test(emo)) {
          tipsSet.add('Sugerencia: Para el enojo, toma 60–90s de pausa y anota la necesidad que no se está cubriendo.');
        } else if (/alegr|joy|happy/.test(emo)) {
          tipsSet.add('Sugerencia: Para alegría, registra qué la provocó y planifica repetirlo esta semana.');
        }
      }
    }

    // 3) final fallback
    if (tipsSet.size === 0) {
      tipsSet.add('Sugerencia: Anima al estudiante a escribir 3 cosas por las que está agradecido hoy.');
    }

    this.suggestions = Array.from(tipsSet).slice(0, 6);
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
          text: this.cleanMessageText(response.bot_response),
          timestamp: new Date(),
          originalData: response
        });
        
        console.log(`📊 DEBUG: Nuevas entradas agregadas. Total entradas actuales: ${this.entries.length}`);

        this.isLoading = false;
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
      // Close mobile journals panel when a selection is made
      this.showMobileJournals = false;
      return;
    }
    this.loadConversationMessages(conversationId);
    // Close mobile journals panel after loading a conversation on mobile
    this.showMobileJournals = false;
  }

  createNewJournal() {
    // Create a local temporary conversation id and select it without calling the backend.
    const tempId = `local-${Date.now()}`;
  this.localTempIds.push(tempId);
    // Use selectConversation so the UI clears messages for a local conversation
    // (selectConversation will set currentConversationId/selectedConversationId and
    // reset entries to the welcome message for local temps).
    this.selectConversation(tempId as any);

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

    // Provide a stable default name based on the conversation id so list reordering
    // (for example when creating a new local diary at the front) does not change
    // the displayed name of other diaries.
    // If the id is numeric, use it directly; for local temp ids (local-<timestamp>)
    // use the timestamp suffix to keep it human-readable.
    if (/^\d+$/.test(key)) {
      return `Diario #${key}`;
    }

    if (key.startsWith('local-')) {
      // show last 6 digits of timestamp for brevity
      const suffix = key.slice(6);
      return `Diario ${suffix.slice(-6)}`;
    }

    // Generic fallback
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
            text: message.sender === 'bot' ? this.cleanMessageText(message.text) : message.text,
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
    const normalize = (s: string) => {
      if (!s) return '';
      return s.toString().toLowerCase().normalize('NFD').replace(/\p{Diacritic}/gu, '').trim();
    };
    const key = normalize(emotion);
    const map: { [k: string]: string } = {
      'joy': '😊', 'happy': '😊', 'alegria': '😊',
      'sadness': '😢', 'sad': '😢', 'tristeza': '😢',
      'anger': '😠', 'angry': '😠', 'ira': '😠', 'enojo': '😠',
      'fear': '😨', 'miedo': '😨',
      'surprise': '😲', 'sorpresa': '😲',
      'disgust': '🤢', 'disgusted': '🤢', 'asco': '🤢',
      'neutral': '😐', 'others': '😐', 'other': '😐'
    };
    return map[key] || '😐';
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