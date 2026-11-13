import {request} from './http';
import {session} from '../lib/session';
let identity='',cache=new Map(),pending=new Map();
let active=0;const queue=[];
function scheduled(read){return new Promise((resolve,reject)=>{queue.push({read,resolve,reject});drain();});}
function drain(){while(active<2&&queue.length){const job=queue.shift();active++;Promise.resolve().then(job.read).then(job.resolve,job.reject).finally(()=>{active--;drain();});}}
// Cache per Lead, so filtering or moving between pages does not reread shared IDs.
export async function requestBranchBills(ids,refresh=false) {
 const login=JSON.stringify([session.user,session.roles,session.csrf_token]);
 if(login!==identity){identity=login;cache=new Map();pending=new Map();}
 const names=[...new Set(ids)].sort(),cacheForLogin=cache,pendingForLogin=pending;
 const missing=names.filter(name=>!pending.has(name)&&(refresh||!cache.has(name)||Date.now()-cache.get(name).at>60000));
 for(let start=0;start<missing.length;start+=200){
  const batch=missing.slice(start,start+200),deferred=new Map();
  for(const name of batch){let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});promise.catch(()=>{});pendingForLogin.set(name,promise);deferred.set(name,{resolve,reject});}
  const token=session.csrf_token;
  scheduled(()=>request('life_slimming.api.cc_report_bills.run',{args:{leads:JSON.stringify(batch)},csrfToken:token})).then(response=>{
   for(const name of batch){const data=response.message?.leads?.[name]??null;cacheForLogin.set(name,{at:Date.now(),data});deferred.get(name).resolve(data);}
  },error=>{for(const name of batch)deferred.get(name).reject(error);}).finally(()=>{for(const name of batch)pendingForLogin.delete(name);});
 }
 const values=await Promise.all(names.map(name=>pendingForLogin.get(name)||Promise.resolve(cacheForLogin.get(name)?.data??null)));
 return Object.fromEntries(names.map((name,i)=>[name,values[i]]));
}
