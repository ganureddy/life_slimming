import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivate, Router, RouterStateSnapshot } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { ApiUrls } from '../apiUrls';
@Injectable({
  providedIn: 'root'
})
export class AuthGuardService implements CanActivate {

  permissions: any = []
  userRole: any = []
  ignoringRoutes = [
    // "/home/user-management",
    "/home/dashboard"
  ]
  constructor(
    private http: HttpClient,
    private toastr: ToastrService,
    private router: Router
  ) { }


  canActivate(route: ActivatedRouteSnapshot, state: RouterStateSnapshot) {
    let user: any = JSON.parse(localStorage.getItem('UserDetails') || 'null')
    console.log("Auth service ====", route?.routeConfig?.path, state.url);
    if (state.url == '/') {
      console.log("if")
      if (user) {
        this.router.navigate(['/timeslots'])
        return false;
      }
      return true;
    } else {
      console.log("else")
      if (!user) {
        this.router.navigate([''])
        return false;
      }
      return true
      // return this.checkUserManagementRouting(state.url.split('?')[0] )
    }


  }



  // checkUserManagementRouting(stateUrl: any) {

  //   let ignoreRouteExist = this.ignoringRoutes.some(res => stateUrl.includes(res))
  //   if (ignoreRouteExist) return true
  //   return this.getUserPermissionListData().then((res: any) => {
  //     let temp = res.some((el: any) => {
  //       return ((el?.route_link == stateUrl && el.read))
  //     })
  //     if (!temp) this.toastr.error('No Access for this page')
  //     return temp ? true : false
  //   })
  // }
  // async getUserPermissionListData() {
  //   let userDetails = JSON.parse(localStorage.getItem('UserDetails') || 'null')
  //   if (userDetails) {
  //     let ezyRolesOfUser = userDetails?.roles.filter((res: any) => {
  //       if (res?.role.toLowerCase().includes('ezy-')) {
  //         return res
  //       }
  //     })
  //     if (ezyRolesOfUser.length <= 1) {
  //       return new Promise((resolve, reject) => {
  //         this.http.get(`${ApiUrls.roles_permission}/${ezyRolesOfUser?.[0]?.role}`, {
  //           params: {
  //             fields: JSON.stringify(['*'])
  //           }
  //         }).subscribe((res: any) => {
  //           if (res?.data) {
  //             resolve(res.data?.permission_list)
  //           }
  //         })
  //       })
  //     } else {
  //       this.toastr.error("user has more ezy roles")
  //     }
  //   }

  // }


}
