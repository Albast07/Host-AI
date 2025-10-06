import { Routes } from '@angular/router';
import { JournalComponent } from './components/journal/journal.component';
import { DashboardComponent } from './components/dashboard/dashboard.component';
import { LoginComponent } from './components/login/login.component';
import { RegisterComponent } from './components/register/register.component';
import { authGuard } from './guards/auth.guard';
import { teacherGuard } from './guards/teacher.guard';
import { studentGuard } from './guards/student.guard';

export const routes: Routes = [
  { path: '', component: JournalComponent, canActivate: [authGuard, studentGuard] },
  { path: 'login', component: LoginComponent },
  { path: 'register', component: RegisterComponent },
  { path: 'dashboard', component: DashboardComponent, canActivate: [teacherGuard] },
  { path: '**', redirectTo: '' }
];