import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { ScheduledTimeSlotsComponent } from './scheduled-time-slots/scheduled-time-slots.component';
import { AuthGuardService } from './shared/auth/auth-guard.service';

const routes: Routes = [
  // { path: '',canActivate:[AuthGuardService], loadChildren: () => import('./auth/login/login.module').then(m => m.LoginModule) },
  {
  path:'',
  // canActivate:[AuthGuardService],
  component:ScheduledTimeSlotsComponent
}];

@NgModule({
  imports: [RouterModule.forRoot(routes, { useHash: true })],
  exports: [RouterModule]
})
export class AppRoutingModule { }
