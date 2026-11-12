export const reportTabs = [
 {key:'visits',path:'',name:'ccvisit',label:'📊 CC — BRANCH VISITS REPORT'},
 {key:'agents',path:'agents',name:'ccvisit-agents',label:'🎧 AGENT REPORT'},
 {key:'marketing',path:'marketing',name:'ccvisit-marketing',label:'📣 LEAD & DIGITAL MARKETING REPORT'},
 {key:'consultants',path:'consultants',name:'ccvisit-consultants',label:'👥 CONSULTANT / MANAGER REPORT'},
 {key:'cluster',path:'cluster',name:'ccvisit-cluster',label:'🧩 CLUSTER REPORT'},
 {key:'agent360',path:'activity',name:'ccvisit-activity',label:'🔗 AGENT 360'},
 {key:'journey',path:'journey',name:'ccvisit-journey',label:'🧭 LEAD JOURNEY'},
];
export const reportAliases={branch:'visits',visits:'visits',agent:'agents',agents:'agents',a360:'agent360',agent360:'agent360',cvx:'convox',convox:'convox',lead:'marketing',marketing:'marketing',cm:'consultants',consultants:'consultants',cluster:'cluster',journey:'journey',nofollowup:'nofollowup',untouched:'untouched'};
export function reportRoute(tab,query={}) {
 const clean={...query};delete clean.tab;
 const sub={convox:'convox',nofollowup:'no-follow-up',untouched:'untouched'}[tab];
 return {path:'/ccvisit'+(sub?'/agents/'+sub:(reportTabs.find(x=>x.key===tab)?.path?'/'+reportTabs.find(x=>x.key===tab).path:'')),query:clean};
}
