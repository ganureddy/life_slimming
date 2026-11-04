window.LIFE_CALL_DONE=function(j){try{j=typeof j==='string'?JSON.parse(j):j;}catch(e){j=null;}
  if(CCX.active&&j&&j.callId===CCX.active.id){CCX.active.native=j||null;CCX.active.ended=Date.now();ccxStore(ccxAK(),CCX.active);
    if(CCX.sheet){const tm=ccxTiming(CCX.active);CCX.sheet.tm=tm;if(!CCX.sheet.conn&&tm.status==='Answered')CCX.sheet.conn='Connected';ccxRender();}else ccxAfterCall();
    ccxAdCallEnded();return;}
  /* exact timing arrived after the agent already saved (sheet filled during the call) */
  if(j&&j.callId&&CCX.lastIds.includes(j.callId))ccxApiSelf({action:'timing',id:j.callId,call_status:j.status||'Unknown',talk_seconds:+j.talk||0,ring_seconds:+j.ring||0,started_on:j.start?ccxIso(new Date(+j.start)):'',data_source:'Phone Call Log'}).catch(()=>{});
};

function ccxTiming(a){
  const now=Date.now();
  if(a.native&&(a.native.talk!=null||a.native.status)){const n=a.native;return {src:'Phone Call Log',status:n.status||'Unknown',talk:+n.talk||0,ring:+n.ring||0,start:n.start?ccxIso(new Date(+n.start)):ccxIso(new Date(a.t)),end:ccxIso(new Date(+n.end||(n.start?+n.start+((+n.ring||0)+(+n.talk||0))*1000:now)))};}
  if(window.LifeApp&&typeof window.LifeApp.getCallLog==='function'){try{const arr=JSON.parse(window.LifeApp.getCallLog(String(a.t-60000))||'[]'),d=String(a.tel||'').slice(-10);const hit=arr.filter(x=>String(x.number||'').replace(/\D/g,'').slice(-10)===d&&x.type==='Outgoing'&&(!x.callId||x.callId===a.id)&&Math.abs((+x.start)-a.t)<=5000).sort((x,y)=>Math.abs((+x.start)-a.t)-Math.abs((+y.start)-a.t))[0];
    if(hit)return {src:'Phone Call Log',status:hit.status||(+hit.talk>0?'Answered':'Not Answered'),talk:+hit.talk||0,ring:+hit.ring||0,start:ccxIso(new Date(+hit.start)),end:ccxIso(new Date(+hit.end||(+hit.start+((+hit.ring||0)+(+hit.talk||0))*1000)))};}catch(e){}}
  return {src:'App Timer',status:'',talk:Math.round((now-a.t)/1000),ring:0,start:ccxIso(new Date(a.t)),end:ccxIso(new Date(now)),approx:1};
}

