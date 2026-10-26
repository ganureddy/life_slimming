<script setup>
import {computed} from 'vue';
import {fdate} from '../../lib/client-info';
import {plainText} from '../../lib/client-profile-sections';
const props=defineProps({record:Object});const row=computed(()=>props.record.row);
const pick=keys=>keys.map(k=>row.value[k]).find(v=>typeof v==='string'&&v);
const title=computed(()=>pick(['subject','title','complaint_title','concern','complaint_type','concern_type','category','issue_type','diet_plan_name','plan_name'])||row.value.name);
const status=computed(()=>pick(['status','workflow_state','resolution_status'])||'');
const text=computed(()=>pick(['description','details','complaint_details','concern_details','remarks','notes']));
const resolution=computed(()=>pick(['resolution','resolution_details','action_taken','closing_remarks']));
const tone=computed(()=>/closed|resolved|completed|done/i.test(status.value)?'ok':/high|critical|urgent/i.test(pick(['priority','severity'])||'')?'neg':'warn');
const skip=new Set(['name','owner','modified_by','creation','modified','docstatus','idx','doctype','patient','client','customer','naming_series','amended_from']);
const extras=computed(()=>props.record.fields.filter(f=>['Data','Select','Link','Date','Currency','Int','Float'].includes(f.fieldtype)&&!skip.has(f.fieldname)&&row.value[f.fieldname]!=null&&row.value[f.fieldname]!==''&&typeof row.value[f.fieldname]!=='object').slice(0,8));
</script>
<template><article class="c3-card c3-accent" :class="'tone-'+tone"><header class="c3-card-h"><div><b>{{title}}</b><small>{{record.doctype}} {{row.name}}, {{fdate(pick(['complaint_date','concern_date','date','opening_date','posting_date','from_date'])||row.creation)}}</small></div><span v-if="status" class="c3-pill" :class="'tone-'+tone">{{status}}</span></header><p v-if="text" class="c3-fu-remark">{{plainText(text)}}</p><p v-if="resolution" class="c3-fu-resp">✅ {{plainText(resolution)}}</p><div class="c3-grid c3-g3"><div v-for="f in extras" :key="f.fieldname" class="c3-kv"><small>{{f.label||f.fieldname}}</small><b>{{f.fieldtype==='Date'?fdate(row[f.fieldname]):row[f.fieldname]}}</b></div></div></article></template>
