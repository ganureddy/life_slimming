import { ccCore } from '../api/cc-core';
import { session } from './session';
let user='', cached=null, checkedAt=0, pending=null;
export function ccPermissions(refresh=false) {
  if(user!==session.user){user=session.user;cached=null;checkedAt=0;pending=null;}
  if(pending)return pending;
  if(!refresh&&cached&&Date.now()-checkedAt<60000)return Promise.resolve(cached);
  const requestUser=user;
  const request=ccCore('perm').then(result=>{if(user===requestUser){cached=result;checkedAt=Date.now();}return result;}).finally(()=>{if(pending===request)pending=null;});
  pending=request;
  return request;
}
