import { ApiUrls } from './apiUrls';
// import { LoaderService } from './loader.component';
import { HostListener, Injectable } from '@angular/core';
import {
  HttpRequest,
  HttpHandler,
  HttpEvent,
  HttpInterceptor,
  HttpResponse
} from '@angular/common/http';
import { Observable, of, Subject, throwError } from 'rxjs';
import { finalize, map, catchError, takeUntil, tap, filter } from 'rxjs/operators';
import { ActivatedRoute, ActivationEnd, ChildActivationEnd, NavigationEnd, NavigationStart, Router } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { LocationStrategy } from '@angular/common';
import { LoaderService } from './loader.component';

@Injectable()
export class ApiCallInterceptor implements HttpInterceptor {
  private pendingHTTPRequests$ = new Subject<void>();
  apiCount = 0;
  nonLoadingApis: any = []
  messageLoaderApis: any = []
  private cache = new Map<string, any>();
  constructor(
    private loader: LoaderService,
    private router: Router,
    private toastr: ToastrService,
    private activatedRoute: ActivatedRoute,
    private location: LocationStrategy,


  ) {
    this.router.events
      .pipe(filter((event) => event instanceof NavigationStart))
      .subscribe((event: any) => {
        if (event.restoredState) {
          this.cancelPendingRequests();
        }
      });
    // location.onPopState((res) => {
    //   this.router.events.subscribe(event => {
    //     if (event instanceof NavigationEnd) {
    //       this.cancelPendingRequests();
    //     }
    //   })

    // });
  }

  public cancelPendingRequests() {
    this.pendingHTTPRequests$.next();
  }

  public onCancelPendingRequests() {
    return this.pendingHTTPRequests$.asObservable();
  }

  intercept(request: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
    this.apiCount++;
    const body = request.body;
    let withCredentials = true;
    if (body instanceof FormData) {
      if (body.get('cmd') == 'login') {
        withCredentials = false;
      }
    }

    // console.log(this.messageLoaderApis);
    if (this.messageLoaderApis.indexOf(request?.url) != -1) {
      this.loader.showLoader('loader2');
    } else if (this.nonLoadingApis.indexOf(request?.url) == -1) {
      this.loader.showLoader('loader1');
    }
    let temp = request.clone({
      url: request.url.replace(/%/, '%25').replace('#', '%23'),
      // withCredentials: withCredentials,
      setHeaders: {
        // 'Access-Control-Allow-Origin':"*"
        'cache-control': "no-cache"
      }
    });

    return next.handle(temp).pipe(map(event => {
      return event;
    }), finalize(() => {
      if (this.nonLoadingApis.indexOf('api/api/' + request.url) == -1) {
        this.apiCount--;
        if (this.apiCount <= 0) {
          this.loader.setLoaderMessage(null)
          this.loader.hideLoader();
        }
      }
    }), catchError(err => {

      if (err.status === 401 || err.error.exc_type == "CSRFTokenError") {
        this.toastr.error(err?.error?.message)
        localStorage.clear()
        this.router.navigate(['']);
      }
      if (err.status === 500) {
        this.toastr.error("Internal Error 500");
      }
      if (err.status === 403) {
        this.toastr.error("Forbidden Error 403")
      }
      if (err.status === 409) {
        this.toastr.error("Already Exists");
      }
      if (err.status === 400) {
        this.toastr.error("Bad Request");
      }
      return throwError(err);
    })
    ).pipe(takeUntil(this.onCancelPendingRequests()));
  }



}
