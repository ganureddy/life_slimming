import { environment } from './../../environments/environment';
const domain = environment.apiDomian + '/api/';

export const Doctypes = {
    branch:"Branch",
    users: "User",
    serviceRoom:"Service Room",
    patientAppointment:'Patient Appointment',
    patient:'Patient',
    therapyType:'Therapy Type',
    healthcareServiceUnit:'Healthcare Service Unit'
}
export const ApiUrls = {
    login: domain + 'method/login',
    logout: domain + 'method/logout',
    users: domain + `resource/${Doctypes.users}`,
    scheduledImports:domain+`resource/${Doctypes.branch}`,
    serviceRoom:domain+`resource/${Doctypes.serviceRoom}`,
    execute:domain+`method/life_slimming.life_slimming.report.appointment_slots.appointment_slots.execute`,
    patientAppointment:domain+`resource/${Doctypes.patientAppointment}`,
    postPatientAppointment:domain+`method/life_slimming.book_appointment.get_create_appointment`,
    get_update_appointment:domain+`method/life_slimming.book_appointment.get_update_appointment`,
    patient:domain+`resource/${Doctypes.patient}`,
    therapyType:domain+`resource/${Doctypes.therapyType}`,
    healthcareServiceUnit:domain+`resource/${Doctypes.healthcareServiceUnit}`,
    get_availability_data:domain+`method/life_slimming.get_availability_data.get_availability_data_for_frontend`
}