<script setup>
import {computed} from 'vue';
import {agentBenchmarks} from '../../../lib/cc-report-scorecard';
import CCDataTable from '../CCDataTable.vue';
import {downloadCsv} from '../../../lib/cc';
const props=defineProps({data:Object,range:Object,owner:String});
const benchmark=computed(()=>agentBenchmarks(props.data,props.range,props.owner));
const name=computed(()=>props.data?.agent_names?.[props.owner]||props.owner);
const format=(value,type)=>type==='percent'?Number(value).toFixed(1)+'%':(type==='money'?'₹':'')+Math.round(value).toLocaleString('en-IN');
const columns=[{key:'label',label:'Metric'},{key:'value',label:'Selected agent',value:r=>format(r.value,r.type)},{key:'average',label:'Team Average',value:r=>format(r.average,r.type)},{key:'best',label:'Team Best',value:r=>format(r.best,r.type)},{key:'difference',label:'vs Average',value:r=>r.difference===null?'—':(r.difference>=0?'▲ ':'▼ ')+Math.abs(r.difference).toFixed(1)+'%'},{key:'rank',label:'Rank'}];
const share=key=>{const total=benchmark.value.core.reduce((n,r)=>n+r[key],0);return total?((benchmark.value.own?.[key]||0)/total*100).toFixed(1)+'%':'—';};
</script>
<template><details open class="arx-sec cc-agent-scorecard"><summary class="arx-sh">🏅 Agent Scorecard vs Team</summary><div class="arx-ah"><span class="arx-av">{{name.split(/\s+/).map(s=>s[0]).join('').slice(0,2)}}</span><div><h3>{{name}}</h3><p>{{owner}}</p></div><div class="arx-ah-r"><div class="arx-badge"><b>{{share('booked')}}</b><span>Share of team bookings</span></div><div class="arx-badge"><b>{{share('revenue')}}</b><span>Share of team revenue</span></div></div></div><CCDataTable :columns="columns" :rows="benchmark.rows"><template #cell-difference="{row}"><span :class="{better:row.difference!==null&&(row.inverse?row.difference<=0:row.difference>=0)}">{{columns[4].value(row)}}</span></template></CCDataTable><p class="arx-note">Team average, best and rank use {{benchmark.core.length}} core agents: at least 10% of the top agent’s leads or appointments, including the selected agent. Lower is better for Not Visited and Balance.</p><button @click="downloadCsv('agent-scorecard.csv',columns,benchmark.rows)">Export scorecard CSV</button></details></template>
<style scoped>.arx-ah{padding:16px;display:flex;gap:12px;align-items:center;flex-wrap:wrap}.arx-ah h3,.arx-ah p{margin:0}.arx-av{display:grid;place-items:center;width:48px;height:48px;background:#e6f2e7;color:#164b32;border-radius:12px;font-weight:800}.arx-ah-r{display:flex;gap:12px;margin-left:auto;flex-wrap:wrap}.arx-badge{display:grid;gap:4px;padding:10px;background:#f2f7ee;border:1px solid #d7e3d9;border-radius:8px}.arx-badge span{font-size:11px}.arx-note{padding:0 14px}.better{font-weight:700;color:#176335}</style>
