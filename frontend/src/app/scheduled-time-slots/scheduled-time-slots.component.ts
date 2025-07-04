import { HttpClient } from '@angular/common/http';
import { Component, ElementRef, EventEmitter, OnInit, ViewChild } from '@angular/core';
import { ApiUrls } from '../shared/apiUrls';
import * as moment from 'moment';
import * as $ from 'jquery';
import { Router } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { debounceTime } from 'rxjs';
import { NgForm } from '@angular/forms';
import { ToastrService } from 'ngx-toastr';
@Component({
  selector: 'app-scheduled-time-slots',
  templateUrl: './scheduled-time-slots.component.html',
  styleUrls: ['./scheduled-time-slots.component.scss']
})
export class ScheduledTimeSlotsComponent implements OnInit {
  @ViewChild('scrollableTable1') scrollableTable1: ElementRef | undefined;
  onSearch=new EventEmitter()
  onSearchConcern=new EventEmitter()
  branchList: any=[];
  selectedBranch:any=''
  allRoomsDataByBranchName: any=[];
  assigningAllBookedSlotsToRooms:any =[];
  selectedDate:any
  userDetails: any;
  searchFilters:any={
    customer:'',
    serviceUnitValue:'',
    concern:''
  }
  clientsList:any=[]
  categoriesList: any=[];
  concernList: any;
  newAppointmentData: any={};
  // newClientObj:any={
  //   patient:'kkk'
  // }
  today=new Date()
  editSlotData:any={
    appointment_date:'',
    apponitment_time:''
  }
  availableSlots: any={};
  finalDataForBookedSlots: any;
  moment=moment
  openModelType: any;
  constructor(
    public http:HttpClient,
    public router : Router,
    public modal : NgbModal,
    public toastr:ToastrService
  ) { }

  ngOnInit(): void {
    this.userDetails = JSON.parse(localStorage.getItem('UserDetails') || 'null')
    this.selectedDate=moment().format('YYYY-MM-DD')
    this.getBranchList()
    // setTimeout(() => {
    //   let el:any = document.getElementById('04:00 PM');
    //   el.scrollIntoViewIfNeeded({
    //     block: 'center',
    //     behavior: 'smooth',
    //   });
    //   // console.log(el)
    //   // el.scrollLeft += 20;
    // }, 5000);
    this.onSearch.pipe(debounceTime(500)).subscribe((res:any)=>{
      console.log('ssssssssss')
      this.getClients()
    })
    this.onSearchConcern.pipe(debounceTime(500)).subscribe((res:any)=>{
      this.getConcern(this.searchFilters?.serviceUnitValue)
    })
    
    this.getCategory()
    
   
  }
  getBranchList(){
    this.http.get(ApiUrls.scheduledImports).subscribe((res:any)=>{
      if(res?.data){
        this.branchList=res?.data
        this.selectedBranch = this.branchList[0]?.name
        this.getAllRooms().then((roomData:any)=>{
          if(roomData){
            this.getData()
          }
        })
      }
    })
  }
  getAllRooms(){
    return new Promise((resolve,reject)=>{
      let queryParams:any={filters:[]}
      queryParams.filters.push(['branch','=',this.selectedBranch])
      this.http.get(ApiUrls.serviceRoom,{
        params:{
          filters:JSON.stringify(queryParams?.filters)
        }
      }).subscribe((res:any)=>{
        if(res?.data){
          this.allRoomsDataByBranchName=res?.data
          resolve(true)
        }
      })
    })
   
  }
  getData(){
    
    let data={
      date:moment(this.selectedDate).format('DD-MM-YYYY'),
      branch:this.selectedBranch
    }
    this.http.get(ApiUrls.execute,{
        params:{
          filters:JSON.stringify(data)
        }
      }
     )
     let queryParams:any={filters:[]}
     queryParams.filters.push(['appointment_date','=',moment(this.selectedDate).format('YYYY-MM-DD')])
     queryParams.filters.push(['branch','=',this.selectedBranch])
     queryParams.filters.push(['call_back_status','!=','Cancel'])
     this.http.get(ApiUrls?.patientAppointment,{
      params:{
        filters:JSON.stringify(queryParams.filters),
        fields:JSON.stringify(['*']),
        limit_page_length:'none'
      }
     })
     .subscribe((res:any)=>{
      console.log(res)
      if(res?.data){
        // console.log(res?.message?.[1])
        // let allbookedSlots=res?.message?.[1]
        let allbookedSlots=res?.data
        
        console.log(this.assigningAllBookedSlotsToRooms)
        this.divideTimeSlots().then((slots:any)=>{
          console.log(slots)
          let tempSlots:any=[]
          slots.forEach((sl:any)=>{
            let slotDetails:any={}
            slotDetails['slot']=moment(sl?.slot, "HH:mm:ss").format("hh:mm A")
            slotDetails['appointments']=[]
            console.log(allbookedSlots)
            this.allRoomsDataByBranchName.forEach((element:any) => {
              let temp = allbookedSlots.filter((pl:any)=>(pl?.service_room == element?.name) && (moment(pl?.appointment_time, "HH:mm:ss").format("hh:mm A")==moment(sl?.slot, "HH:mm:ss").format("hh:mm A")))
              // if(!element['appointments']) element['appointments']=[] 
              console.log(temp)
              let obj={
                // slot:moment(sl?.slot, "HH:mm:ss").format("hh:mm A"),
                date:moment(this.selectedDate).format('YYYY-MM-DD'),
                slot:moment(sl?.slot, "HH:mm:ss").format("hh:mm A"),
                bookedDetails:temp,
                service_room:element?.name
              }
              // sl['service_room'] =element?.name
              // sl['appointments']=[]
              slotDetails['appointments'].push(obj)
            });
            tempSlots.push(slotDetails)
          })
          
          this.finalDataForBookedSlots={
            columns:this.allRoomsDataByBranchName,
            data:tempSlots
          }
          console.log(this.finalDataForBookedSlots)




          // this.allRoomsDataByBranchName.forEach((element:any) => {
          //   slots.forEach((sl:any)=>{
          //     let temp = allbookedSlots.filter((pl:any)=>(pl?.service_room == element?.name) && (moment(pl?.appointment_time, "HH:mm:ss").format("hh:mm A")==moment(sl?.slot, "HH:mm:ss").format("hh:mm A")))
          //     if(!element['appointments']) element['appointments']=[] 
          //     let obj={
          //       slot:moment(sl?.slot, "HH:mm:ss").format("hh:mm A"),
          //       bookedDetails:temp
          //     }
          //     element['appointments'].push(obj)
          //   })
          // });
          // console.log(this.allRoomsDataByBranchName)
          setTimeout(() => {
            let currDate = moment(new Date(),'hh:mm A')
            let id:any=''
            if(moment({hour:8,minute:0,second:0,}).isBefore(currDate) && currDate.isBefore(moment({hour:21,minute:0,second:0,}))){
              let dd = moment(currDate).format('hh:mm A')
              if(parseInt(dd.split(':')[1])<=30){
                id = moment().set({minute:0}).format('hh:mm A')
                console.log(id)
              }else{
                id = moment().set({minute:30}).format('hh:mm A')
              }
              console.log(id)
              let el:any = document.getElementById(id);
              el.scrollIntoView({
                block: 'center',
                behavior: 'smooth',
              });
            }
            
          }, 500);
          
        })
      }
    })
  }
  divideTimeSlots(){
    return new Promise((resolve,reject)=>{
      var starttime = "08:00:00";
      var interval = "30";
      var endtime = "21:00:00";
      var timeslots = [{slot:starttime}];
      while (starttime != endtime) {
    
        starttime = this.addMinutes(starttime, interval);
        let obj:any={
          slot:starttime
        }
        timeslots.push(obj);
      
      }
      resolve(timeslots)
    })
   
  }
  addMinutes(time:any, minutes:any) {
    var date = new Date(new Date('01/01/2015 ' + time).getTime() + minutes * 60000);
    var tempTime = ((date.getHours().toString().length == 1) ? '0' + date.getHours() : date.getHours()) + ':' +
      ((date.getMinutes().toString().length == 1) ? '0' + date.getMinutes() : date.getMinutes()) + ':' +
      ((date.getSeconds().toString().length == 1) ? '0' + date.getSeconds() : date.getSeconds());
    return tempTime;
  }
  changeFilters(){
    this.getAllRooms().then((roomData:any)=>{
      if(roomData){
        this.getData()
      }
    })
  }
  logout(): void {
   
    this.http.get(ApiUrls.logout).subscribe(()=>{
      localStorage.clear();
      sessionStorage.clear();
      this.router.navigate(['/']);
      window.location.reload()
    })
    
  }
  addModel(addAppointmentModel:any,timeSlot:any,branchDetails:any){
    console.log(timeSlot,branchDetails)
    this.newAppointmentData['timeSlot']=timeSlot?.slot
    this.newAppointmentData['serviceId']=timeSlot?.service_room
    console.log(this.newAppointmentData)
    this.modal.open(addAppointmentModel,{size:'md'})
    this.getClients()
  }
  editModel(editAppointmentModel:any,timeSlot:any,slotDetails:any,eventType:any=null){
    // console.log(timeSlot,branchDetails)
    this.openModelType=eventType
    this.editSlotData={}
    this.availableSlots['avail_slot']=[]
    if(eventType=='edit'){
      this.newAppointmentData['timeSlot']=timeSlot?.slot
      this.newAppointmentData['serviceId']=timeSlot?.service_room
      this.newAppointmentData['name']=slotDetails?.name
      this.newAppointmentData['slotDetails']=slotDetails
      this.editSlotData['call_back_status'] = slotDetails?.call_back_status
    }else{
      this.editSlotData['call_back_status'] = null
    }
    
    console.log(this.newAppointmentData)
    this.modal.open(editAppointmentModel,{size:'lg'})
    if(eventType!='edit'){
      this.getClients()
    }
  }
  getClients(){
    let queryParams:any={filters:[]}
    console.log(this.searchFilters)
    queryParams.filters.push(['branch_name','=',`${this.selectedBranch}`])
    if(this.searchFilters?.customer){
      queryParams.filters.push(['customer','like',`%${this.searchFilters?.customer}%`])
    }
    this.http.get(ApiUrls.patient,{
      params:{
        filters:JSON.stringify(queryParams.filters),
        fields:JSON.stringify(['name','customer'])
      }
    }).subscribe((res:any)=>{
      console.log(res)
      if(res?.data){
        this.clientsList=res?.data
      }
    })
  }
  getCategory(){
    this.http.get(ApiUrls.healthcareServiceUnit).subscribe((res:any)=>{
      console.log(res)
      if(res?.data){
        this.categoriesList=res?.data
      }
    })
  }
  searchClient(eve:any){
    this.searchFilters.customer=eve?.term
    this.onSearch.emit()
  }
  searchConcern(eve:any){
    this.searchFilters.concern=eve?.term
    this.onSearchConcern.emit()
  }
  serviceUnitChange(serviceUnitValue:any){
    console.log(serviceUnitValue)
    this.searchFilters.serviceUnitValue=serviceUnitValue
    this.getConcern(serviceUnitValue)
  }
  getConcern(serviceUnitValue:any){
    let queryParams:any={filters:[]}
    queryParams.filters.push(['healthcare_service_unit','=',`${serviceUnitValue}`])
    if(this.searchFilters?.concern){
      queryParams.filters.push(['name','like',`%${this.searchFilters?.concern}%`])
    }
    this.http.get(ApiUrls.therapyType,{
      params:{
        filters:JSON.stringify(queryParams.filters),
        fields:JSON.stringify(['*'])
      }
    }).subscribe((res:any)=>{
      console.log(res)
      if(res?.data){
        this.concernList=res?.data
      }
    })
  }
  appDateChange(){
    console.log(this.newAppointmentData,this.editSlotData.appointment_date)
    let data={
      "date":moment(this.editSlotData.appointment_date).format('YYYY-MM-DD'),
      "service_room":(this.openModelType=='edit')?this.newAppointmentData?.serviceId:this.editSlotData.service_room,
      "branch":this.selectedBranch
    }
    this.http.get(ApiUrls.get_availability_data,{
      params:data
    }).subscribe((res:any)=>{
      console.log(res)
     if(res?.message?.slot_details){
      this.availableSlots= res?.message?.slot_details[0]
      this.availableSlots?.avail_slot.forEach((el:any)=>{
        el['from_time']=moment(el?.from_time, "HH:mm:ss").format("hh:mm A")
      })
     }
    })
  }
  selectTimeSlot(item:any){
    this.availableSlots?.avail_slot.forEach((el:any)=>el['checked']=false)
    item['checked']=true
    this.newAppointmentData['from_time']=item?.from_time
  }
  changeserviceroom(){
    this.editSlotData.appointment_date=null
    this.availableSlots['avail_slot']=[]
  }
  saveTheForm(form:NgForm){
    if(form.valid){
      let data:any={}
      data={...this.newAppointmentData,...form?.value}
      console.log(data,this.openModelType,this.editSlotData)
      let newobj={
        patient:data?.customer,
        service_room:data?.serviceId,
        concern:data?.concern,
        branch:this.selectedBranch,
        service_unit:data?.serviceUnit,
        appointment_date:this.selectedDate,
        appointment_time:moment(data?.timeSlot,'hh:mm A').format('HH:mm:ss'),
      }
      this.http.get(ApiUrls.postPatientAppointment,{
        params:newobj
      }).subscribe((res:any)=>{
        console.log(res)
        if(res?.message?.status){
          this.getBranchList()
          this.modal?.dismissAll()
          this.toastr.success('Created')
        }else{
          this.toastr.error(res?.message?.message)
        }
      })
    }else{
      form.form.markAllAsTouched()
    }
   
  }
  updateAppointment(form:NgForm){
    console.log(form.value,this.newAppointmentData)
    if(form?.valid){
      let data={}
      if(this.editSlotData.call_back_status=='Re-Scheduled'){
        data={
          call_back_status:form.value?.call_back_status,
          appointment_date:form.value.appointment_date?form.value.appointment_date:'',
          appointment_time:moment(this.newAppointmentData?.from_time,'hh:mm A').format('HH:mm:ss'),
        }
      }else{
        data={
          call_back_status:form.value?.call_back_status,
        }
      }
     
      this.http.get(`${ApiUrls.get_update_appointment}`,{
        params:{
          name:this.newAppointmentData?.name,
          data:JSON.stringify(data)
        }
      }).subscribe((res:any)=>{
        console.log(res)
        if(res?.message?.status){
          this.toastr.success(res?.message?.message)
          this.getBranchList()
          this.modal?.dismissAll()
        }else{
          this.toastr.error(res?.message?.message)
        }
      })
    }else{
      form.form.markAllAsTouched()
    }
  }
  createAppointmentForm(form:NgForm){
    if(form.valid){
      let data:any={}
      data={...this.newAppointmentData,...form?.value}
      console.log(data,this.openModelType,this.editSlotData)
      let newobj={
        patient:data?.customer,
        service_room:form.value?.service_room,
        concern:data?.concern,
        branch:this.selectedBranch,
        service_unit:data?.serviceUnit,
        appointment_date:this.editSlotData.appointment_date,
        appointment_time:moment(this.newAppointmentData['from_time'],'hh:mm A').format('HH:mm:ss'),
      }
      this.http.get(ApiUrls.postPatientAppointment,{
        params:newobj
      }).subscribe((res:any)=>{
        console.log(res)
        if(res?.message?.status){
          this.getBranchList()
          this.modal?.dismissAll()
          this.toastr.success('Created')
        }else{
          this.toastr.error(res?.message.message)
        }
      })
    }else{
      form.form.markAllAsTouched()
    }
   
  }
}
