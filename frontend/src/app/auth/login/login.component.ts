import { Component, OnInit } from '@angular/core';
import { NgForm } from '@angular/forms';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { ApiUrls } from 'src/app/shared/apiUrls';
import { ToastrService } from 'ngx-toastr';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss']
})
export class LoginComponent implements OnInit {
  password: any;
  spinner = false
  errMsg = false
  inputType: any = 'password'
  constructor(
    public router: Router,
    private http: HttpClient,
    private toastr: ToastrService,
  ) { }

  ngOnInit(): void {
  }


  onSubmit(form: NgForm): void {
    this.spinner = true
    if (form.invalid) {
      this.errMsg = true
      this.spinner = false
      setTimeout(() => {
        this.errMsg = false
      }, 2000)
    }
    if (form.valid) {
      const data = {
        usr: form.value.email,
        pwd: form.value.password,
      };

      this.http.get(ApiUrls.login, { params: data }).subscribe((res: any) => {
        this.spinner = true
        if (res?.message == 'Logged In') {
          this.getUserDetails(form.value.email)
          // this.getUserCompanyData(data.usr)
        } else {
          this.spinner = false
          this.toastr.error(res?.message)
        }
      }, (err) => {
        console.log(err);
        if (err.status == 401) {
          this.spinner = false
        }
      })
    }
  }

  showPassword() {
    if (this.inputType == "password") {
      this.inputType = "text"
    }
    else {
      this.inputType = "password"
    }
  }
  // getUserCompanyData(email: string) {

  //   this.http.get(ApiUrls.user_permisions, {
  //     params: {
  //       filters: JSON.stringify([['user', '=', email]]),
  //       fields: JSON.stringify(['*']),
  //       limit_page_length: 'none'
  //     }
  //   }).subscribe((res: any) => {
  //     if (res?.data.length) {
  //       this.getUserDetails(res?.data)

  //     } else {
  //       this.toastr.error("No Company is assigned")
  //     }
  //   })
  // }
  getUserDetails(user: any) {
    // let userCompanyList = companyData

    this.http.get(`${ApiUrls.users}/${user}`, {
      params: {
        fields: JSON.stringify(['*'])
      }
    }).subscribe((res: any) => {
      if (res.data) {
        localStorage.setItem('UserDetails', JSON.stringify(res.data))
        // localStorage.setItem('USERCOMPANY', JSON.stringify(companyData))
        setTimeout((res: any) => this.router.navigate(['timeslots']), 100)
        // this.userManagement.getUserManagementData(res.data).then((result:any)=>{
        //   console.log(result)
        //   if(result){
        //     setTimeout((res:any)=>this.router.navigate(['home/dashboard']),100)
        //     localStorage.setItem('UserDetails',JSON.stringify(res.data))
        //     localStorage.setItem('USERCOMPANY',JSON.stringify(companyData))
        //     localStorage.setItem('userRoutePermission',JSON.stringify(result))
        //   }

        // })
      }
    })
  }
}
