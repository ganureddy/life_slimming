import { request } from '../api/http';
import { apiUrl, apiCredentials } from '../api/config';
import endpoints from '../api/endpoints.json';

// Isolated lifecycle for page-owned dashboard controllers. No global Frappe or
// document patches: reads, timers, listeners and observers die with the Vue page.
export function createDomPageRuntime({ root, session, status }) {
  const doc = root.ownerDocument, win = doc.defaultView;
  const timers = new Set(), intervals = new Set(), listeners = [], observers = new Set(), reads = new Set();
  let alive = true;
  const listen = (target, type, handler, options) => { target.addEventListener(type, handler, options); listeners.push([target,type,handler,options]); };
  const timeout = (fn, ms, ...args) => { const id=win.setTimeout(()=>{timers.delete(id);if(alive)fn(...args);},ms);timers.add(id);return id; };
  const interval = (fn, ms, ...args) => { const id=win.setInterval(()=>{if(alive)fn(...args);},ms);intervals.add(id);return id; };
  const query = selector => root.matches(selector) ? root : root.querySelector(selector);
  const body = new Proxy(root,{get(target,key){if(key==='append'||key==='appendChild')return target[key].bind(target);const v=target[key];return typeof v==='function'?v.bind(target):v;}});
  const document = new Proxy(doc,{get(target,key){
    if(key==='getElementById')return id=>root.id===id?root:root.querySelector('#'+win.CSS.escape(id));
    if(key==='querySelector')return query;
    if(key==='querySelectorAll')return selector=>root.querySelectorAll(selector);
    if(key==='body'||key==='documentElement')return body;
    if(key==='head')return body;
    if(key==='readyState')return 'complete';
    if(key==='addEventListener')return (...args)=>listen(doc,...args);
    if(key==='removeEventListener')return doc.removeEventListener.bind(doc);
    const value=target[key];return typeof value==='function'?value.bind(target):value;
  }});
  function mappedUrl(value) {
    const url = new URL(String(value),win.location.href);
    if(url.origin!==win.location.origin)return url.href;
    const prefix='/api/method/';
    if(url.pathname.startsWith(prefix)){const method=decodeURIComponent(url.pathname.slice(prefix.length));url.pathname=prefix+(endpoints[method]||method);}
    return url.pathname.startsWith('/api/')?apiUrl(url.pathname+url.search):url.href;
  }
  async function fetchPage(input, options={}) {
    if(!alive)throw new DOMException('Page closed','AbortError');
    const controller=new AbortController(), method=String(options.method||'GET').toUpperCase();
    const read=method==='GET'||method==='HEAD'||String(input).includes('/api/method/')&&!/insert|set_value|upload_file|delete|save|share.add|email.make/.test(String(input));
    const headers=new Headers(options.headers);
    let url=mappedUrl(input), actualMethod=method;
    const isApi = new URL(url,win.location.href).origin === new URL(apiUrl('/api/'),win.location.href).origin && new URL(url,win.location.href).pathname.startsWith('/api/');
    if(isApi)headers.set('X-Frappe-CSRF-Token',session.csrf_token||'');
    if(method==='GET'&&Object.values(endpoints).some(endpoint=>url.includes('/api/method/'+endpoint)))actualMethod='POST';
    const abort=()=>controller.abort();options.signal?.addEventListener('abort',abort,{once:true});if(options.signal?.aborted)controller.abort();
    reads.add(controller);status[read?'reads':'writes']++;
    try{return await win.fetch(url,{...options,method:actualMethod,headers,credentials:isApi?apiCredentials():'same-origin',signal:controller.signal});}
    finally{reads.delete(controller);options.signal?.removeEventListener('abort',abort);if(alive)status[read?'reads':'writes']--;}
  }
  const frappe = { session:{user:session.user,user_fullname:session.full_name},csrf_token:session.csrf_token,
    user_roles:session.roles||[],boot:{user:{roles:session.roles||[]}},user:{has_role:role=>session.roles?.includes(role)},
    ready:fn=>timeout(fn,0),msgprint:value=>{status.notice=typeof value==='string'?value:value?.message||'';},
    call(options,args,callback){if(typeof options==='string')options={method:options,args,callback};
      const method=endpoints[options.method]||options.method;
      const read=!/insert|set_value|delete|save|share.add|email.make/.test(method);
      const ctrl=new AbortController();reads.add(ctrl);status[read?'reads':'writes']++;
      const result=request(method,{args:options.args,csrfToken:session.csrf_token,signal:ctrl.signal}).then(body=>{if(alive)options.callback?.(body);return body;},error=>{if(alive&&error.name!=='AbortError'){status.error=error.message;options.error?.(error);}throw error;}).finally(()=>{reads.delete(ctrl);if(alive){status[read?'reads':'writes']--;options.always?.();}});
      if(options.callback||options.error)result.catch(()=>{});return result;
    }};
  class Observer extends win.MutationObserver {constructor(callback){super((...args)=>{if(alive)callback(...args);});observers.add(this);}}
  const window=new Proxy({}, {get(target,key){if(key==='frappe')return frappe;if(key==='csrf_token')return session.csrf_token;if(key==='document')return document;if(key==='addEventListener')return (...args)=>listen(win,...args);if(key==='removeEventListener')return win.removeEventListener.bind(win);if(key==='setTimeout')return timeout;if(key==='setInterval')return interval;if(key==='MutationObserver')return Observer;const v=key in target?target[key]:win[key];return typeof v==='function'&&!/^\p{Lu}/u.test(String(key))?v.bind(win):v;},set(target,key,value){target[key]=value;return true;}});
  return {root,document,window,frappe,fetch:fetchPage,MutationObserver:Observer,setTimeout:timeout,clearTimeout:id=>{timers.delete(id);win.clearTimeout(id);},setInterval:interval,clearInterval:id=>{intervals.delete(id);win.clearInterval(id);},
    upload:async(formData)=>{const response=await fetchPage('/api/method/upload_file',{method:'POST',body:formData});const data=await response.json();if(!response.ok||!data.message?.file_url)throw Error('Upload failed.');return data.message;},
    dispose(){alive=false;reads.forEach(ctrl=>ctrl.abort());timers.forEach(id=>win.clearTimeout(id));intervals.forEach(id=>win.clearInterval(id));listeners.forEach(args=>args[0].removeEventListener(...args.slice(1)));observers.forEach(o=>o.disconnect());}
  };
}
