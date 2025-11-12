import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-onboarding',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './onboarding.component.html',
  styleUrls: ['./onboarding.component.scss']
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
