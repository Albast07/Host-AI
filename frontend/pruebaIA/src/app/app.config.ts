import { ApplicationConfig } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { routes } from './app.routes';

// NOTE: Service worker registration disabled temporarily so the app
// runs without PWA caching while we stabilize assets and deployment.
// To re-enable, restore provideServiceWorker(...) and set enabled based
// on environment / isDevMode() as desired.
export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),
    provideHttpClient()
  ]
};