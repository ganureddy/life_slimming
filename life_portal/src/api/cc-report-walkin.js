import {request} from './http';
import {session} from '../lib/session';
import {createReportLoader} from '../lib/cc-report-loader';
export const requestWalkinDetails=createReportLoader(
 async args=>(await request('life_slimming.api.cc_report_walkin.run',{args,csrfToken:session.csrf_token})).message,
 ()=>[session.user,session.roles,session.csrf_token],60000,
);
