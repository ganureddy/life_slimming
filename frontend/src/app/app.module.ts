import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { ScheduledTimeSlotsComponent } from './scheduled-time-slots/scheduled-time-slots.component';
import { HTTP_INTERCEPTORS, HttpClientModule } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { NgbDropdownModule, NgbModule } from '@ng-bootstrap/ng-bootstrap';
import { ToastrModule } from 'ngx-toastr';
import { ApiCallInterceptor } from './shared/api-call.interceptor';
import { AuthGuardService } from './shared/auth/auth-guard.service';
import { LoaderComponent } from './shared/loader.component';
import {BrowserAnimationsModule} from "@angular/platform-browser/animations";
import { NgSelectModule } from '@ng-select/ng-select';
@NgModule({
  declarations: [
    AppComponent,
    LoaderComponent,
    ScheduledTimeSlotsComponent
  ],
  imports: [
    BrowserModule,
    HttpClientModule,
    FormsModule,
    NgbModule,
    BrowserModule,
    NgSelectModule,
    BrowserAnimationsModule,
    ToastrModule.forRoot(),
    NgbDropdownModule,
    AppRoutingModule
  ],
  providers: [
    {
      useClass: ApiCallInterceptor,
      provide: HTTP_INTERCEPTORS,
      multi: true
    },
    AuthGuardService,
  ],
  bootstrap: [AppComponent]
})
export class AppModule { }
