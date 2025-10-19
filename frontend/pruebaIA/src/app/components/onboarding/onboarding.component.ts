import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-onboarding',
  standalone: true,
  imports: [CommonModule],
  template: `
  <div class="onboarding-backdrop">
    <div class="onboarding-box">
      <div class="onboarding-header">
        <h2>{{ slides[current].title }}</h2>
        <button class="skip" (click)="finish()">Omitir</button>
      </div>

      <div class="onboarding-body">
        <p [innerHTML]="slides[current].body"></p>
      </div>

      <div class="onboarding-footer">
        <div class="dots">
          <span *ngFor="let s of slides; let i = index" [class.active]="i === current"></span>
        </div>
        <div class="controls">
          <button (click)="prev()" [disabled]="current === 0">Anterior</button>
          <button (click)="next()">{{ current === slides.length - 1 ? 'Entendido' : 'Siguiente' }}</button>
        </div>
      </div>
    </div>
  </div>
  `,
  styles: [
    `
    .onboarding-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 2000;
    }
    .onboarding-box {
      width: 92%;
      max-width: 720px;
      background: white;
      border-radius: 12px;
      padding: 20px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    .onboarding-header {
      display:flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
    }
    .onboarding-header h2 { margin: 0; font-size: 1.25rem; }
    .onboarding-header .skip { background: transparent; border: none; color: #667eea; cursor: pointer; }
    .onboarding-body { padding: 18px 0; color: #333; line-height: 1.5; }
    .onboarding-footer { display:flex; justify-content: space-between; align-items: center; }
    .dots { display:flex; gap:6px; }
    .dots span { width:10px; height:10px; border-radius:50%; background:#e6e6e6; display:inline-block; }
    .dots span.active { background:#667eea; }
    .controls button { background:#667eea; color:white; border:none; padding:8px 12px; border-radius:8px; cursor:pointer; }
    .controls button[disabled] { background:#ccc; cursor:not-allowed; }
    `
  ]
})
export class OnboardingComponent {
  @Output() close = new EventEmitter<void>();

  current = 0;

  slides = [
    {
      title: '¿Qué es la app?',
      body: 'Diario Emocional IA es una herramienta educativa para ayudar a estudiantes a registrar y reflexionar sobre sus emociones. Puedes escribir entradas cortas y la IA te dará retroalimentación educativa.'
    },
    {
      title: 'Cómo escribir una entrada',
      body: 'Escribe libremente sobre lo que sientas o pienses. Describe situaciones, sensaciones o pensamientos. No te preocupes por la longitud: con dos o tres frases suele ser suficiente.'
    },
    {
      title: 'Cómo crear nuevos diarios',
      body: 'Para crear un nuevo diario, ve a la sección de "mis diarios" y selecciona "Crear nuevo diario". Luego, elige un nombre y comienza a escribir tus entradas.'
    },
    {
      title: 'Qué hace la IA',
      body: 'La IA analiza tu mensaje y te ofrece preguntas reflexivas y tips educativos para ayudarte a entender lo que sientes (No sustituye a un profesional).'
    },
    {
      title: 'Cómo se usan tus datos',
      body: 'Tus mensajes se almacenan de forma segura para ofrecerte historial y estadísticas. Los profesores ven solo estadísticas agregadas y no textos individuales sin tu consentimiento. Puedes eliminar tu cuenta o solicitar borrado.'
    }
  ];

  next() {
    if (this.current < this.slides.length - 1) {
      this.current++;
    } else {
      this.finish();
    }
  }

  prev() {
    if (this.current > 0) this.current--;
  }

  finish() {
    this.close.emit();
  }
}
