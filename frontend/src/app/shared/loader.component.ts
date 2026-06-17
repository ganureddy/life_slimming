
// import { ChangeDetectionStrategy } from '@angular/compiler/src/compiler_facade_interface';
import { Component, OnInit, ViewChild, ElementRef, ChangeDetectorRef } from '@angular/core';
import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Component({
  selector: 'app-loader',
  template: `
  <div  *ngIf="showLoading" class="content overlay">
    <div *ngIf="loaderName == 'loader1'" class="imgParent">
      <img class="imgGif2" src="../assets/images/unnamed.png">
    </div>
    <div *ngIf="loaderName == 'loader2'" class="imgParent">
      <div class="card">
        <div class="card-body">
          <img class="imgGif" src="../assets/gif/loader.gif">
          <div class="loading_msg">
            <p class="title1">Take a break and relax</p>
            <p class="title2">{{this.message}}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
 
  <ng-content></ng-content>
  `
  ,
  styles: [`
/* Loader 1 */
.loader-1 {
	height: 32px;
	width: 32px;
	-webkit-animation: loader-1-1 4.8s linear infinite;
	        animation: loader-1-1 4.8s linear infinite;
}
.imgParent{
  /* display: flex;
  justify-content: center;
  align-items : center; */
}
.imgGif{
  width: 273px;
  text-align: center;
}
.imgGif2{
  width: 65px;
  height: 45px;
  text-align: center;
}
@-webkit-keyframes loader-1-1 {
	0%   { -webkit-transform: rotate(0deg); }
	100% { -webkit-transform: rotate(360deg); }
}
@keyframes loader-1-1 {
	0%   { transform: rotate(0deg); }
	100% { transform: rotate(360deg); }
}
.loader-1 span {
	display: block;
	position: absolute;
	top: 0; left: 0;
	bottom: 0; right: 0;
	margin: auto;
	height: 32px;
	width: 32px;
	clip: rect(0, 32px, 32px, 16px);
	-webkit-animation: loader-1-2 1.2s linear infinite;
	        animation: loader-1-2 1.2s linear infinite;
}
@-webkit-keyframes loader-1-2 {
	0%   { -webkit-transform: rotate(0deg); }
	100% { -webkit-transform: rotate(220deg); }
}
@keyframes loader-1-2 {
	0%   { transform: rotate(0deg); }
	100% { transform: rotate(220deg); }
}
.loader-1 span::after {
	content: "";
	position: absolute;
	top: 0; left: 0;
	bottom: 0; right: 0;
	margin: auto;
	height: 32px;
	width: 32px;
	clip: rect(0, 32px, 32px, 16px);
	border: 3px solid #FFF;
	border-radius: 50%;
	-webkit-animation: loader-1-3 1.2s cubic-bezier(0.770, 0.000, 0.175, 1.000) infinite;
	        animation: loader-1-3 1.2s cubic-bezier(0.770, 0.000, 0.175, 1.000) infinite;
}
@-webkit-keyframes loader-1-3 {
	0%   { -webkit-transform: rotate(-140deg); }
	50%  { -webkit-transform: rotate(-160deg); }
	100% { -webkit-transform: rotate(140deg); }
}
@keyframes loader-1-3 {
	0%   { transform: rotate(-140deg); }
	50%  { transform: rotate(-160deg); }
	100% { transform: rotate(140deg); }
}

.card{
  width:400px ;
  height:400px;
  border-radius:42px;
}
.loading_msg{
  .title1{
    font-size:24px;
    font-weight:bold;
    margin:0px;
  }
  .title2{
    margin-top:11px;
    /* color:black !important; */
    font-weight:bold;
  }
}
  .overlay {
    text-align: center;
  height: 100%;
  width: 100%;
  position: fixed;
  z-index: 10000;
  top: 0;
  left: 0;
  background-color: rgba(0,0,0, 0.5);
  overflow-x: hidden;
  transition: 0.5s;
  display:flex;
  justify-content:center;
  align-items:center;
}
  `]
})
export class LoaderComponent implements OnInit {
  showLoading = false;
  message:any
  loaderName: any;
  constructor(
    private loaderService: LoaderService,
    private cdr: ChangeDetectorRef
  ) { }

  ngOnInit(): void {
    this.message = ''
    this.loaderService.getLoaderStats().subscribe((res) => {
      this.showLoading = res.status;
      this.loaderName = res.loaderName
      this.cdr.detectChanges();
    });
    this.loaderService.getLoaderMessageStatus().subscribe((result) => {
      if (result) { 
        this.message = result
      }else{
        this.message = 'Processing...'
      }
    });

  }

}

@Injectable({
  providedIn: 'root'
})
export class LoaderService {
  public loader: BehaviorSubject<any> = new BehaviorSubject<any>({
    status:false,
    loaderName:'loader1'
  });
  public loaderMessage: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(false);
  constructor() { 
  }
  showLoader(loaderName:any) {
    let obj={
      status:true,
      loaderName:loaderName
    }
    this.loader.next(obj);
  }
  hideLoader() {
    let obj={
      status:false,
      loaderName:''
    }
    this.loader.next(obj);
  }
  getLoaderStats() {
    return this.loader.asObservable();
  }

  setLoaderMessage(message:any) {
    this.loaderMessage.next(message);
  }
  getLoaderMessageStatus() {
    return this.loaderMessage.asObservable();
  }
}