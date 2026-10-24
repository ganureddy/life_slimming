<script setup>
import { useClientRegistration } from '../composables/useClientRegistration';
const { root,fileInput,form,errors,touched,links,registrations,loading,loadError,busy,saveError,saved,pdFile,toastMessage,
  ageText,ageHint,risk,initials,risks,validate,closeLinks,searchLink,chooseLink,linkKey,loadRegistrations,resetForm,pickFile,saveClient,openBilling } = useClientRegistration();
</script>

<template>
<div id="cr-root" ref="root" @click="closeLinks">
 <p v-if="saveError" role="alert" class="registration-error">{{ saveError }}</p>
 <p v-if="saved" role="status" class="registration-success">Client {{ saved.name }} registered. <button type="button" @click="openBilling">Open Billing</button></p>
 <fieldset :disabled="busy || !!saved" class="registration-fields">


<div class="wrap">
 <div><!-- ================= FORM ================= -->

  <div class="card"><h3><span class="stp">1</span>Client Identity</h3>
   <div class="fgrid">
    <div class="fg" id="fg-fName" :class="{'has-err':errors.fName,ok:touched.fName &amp;&amp; !errors.fName}"><label>Client Name <span class="req">*</span></label><input id="fName" v-model="form.fName" @blur="validate('fName')" placeholder="Full name"><span class="err" id="e-fName">{{ errors.fName }}</span></div>
    <div class="fg"><label>Alias Name</label><input id="fAlias" v-model="form.fAlias" @blur="validate('fAlias')" placeholder="Known as / nickname"></div>
    <div class="fg" id="fg-fGender" :class="{'has-err':errors.fGender,ok:touched.fGender &amp;&amp; !errors.fGender}"><label>Gender <span class="req">*</span></label><select id="fGender" v-model="form.fGender" @blur="validate('fGender')"><option value="">— select —</option><option>Female</option><option>Male</option><option>Other</option></select><span class="err" id="e-fGender">{{ errors.fGender }}</span></div>
    <div class="fg" id="fg-fDob" :class="{'has-err':errors.fDob,ok:touched.fDob &amp;&amp; !errors.fDob}"><label>Date of Birth <span class="req">*</span></label><input type="date" id="fDob" v-model="form.fDob" @blur="validate('fDob')"><span class="hint" id="ageHint">{{ ageHint }}</span><span class="err" id="e-fDob">{{ errors.fDob }}</span></div>
    <div class="fg"><label>Age (auto)</label><input id="fAge" :value="ageText" readonly style="background:var(--g50);font-weight:800" placeholder="—"></div>
    <div class="fg"><label>Occupation</label><input id="fOcc" v-model="form.fOcc" @blur="validate('fOcc')" placeholder="e.g. Software Engineer / Homemaker"></div>
   </div>
  </div>

  <div class="card"><h3><span class="stp">2</span>Contact & Address</h3>
   <div class="fgrid">
    <div class="fg" id="fg-fPhone" :class="{'has-err':errors.fPhone,ok:touched.fPhone &amp;&amp; !errors.fPhone}"><label>Phone Number <span class="req">*</span></label><input id="fPhone" v-model="form.fPhone" @blur="validate('fPhone')" maxlength="13" inputmode="numeric" placeholder="10-digit mobile"><span class="err" id="e-fPhone">{{ errors.fPhone }}</span></div>
    <div class="fg" id="fg-fAlt" :class="{'has-err':errors.fAlt,ok:touched.fAlt &amp;&amp; !errors.fAlt}"><label>Alternative Number</label><input id="fAlt" v-model="form.fAlt" @blur="validate('fAlt')" maxlength="13" inputmode="numeric" placeholder="Alternate contact"><span class="err" id="e-fAlt">{{ errors.fAlt }}</span></div>
    <div class="fg" id="fg-fEmail" :class="{'has-err':errors.fEmail,ok:touched.fEmail &amp;&amp; !errors.fEmail}"><label>Email ID</label><input type="email" id="fEmail" v-model="form.fEmail" @blur="validate('fEmail')" placeholder="name@email.com"><span class="err" id="e-fEmail">{{ errors.fEmail }}</span></div>
    <div class="fg" id="fg-fArea" :class="{'has-err':errors.fArea,ok:touched.fArea &amp;&amp; !errors.fArea}"><label>Client Area <span class="req">*</span></label><input id="fArea" v-model="form.fArea" @blur="validate('fArea')" placeholder="e.g. Kukatpally, Miyapur"><span class="err" id="e-fArea">{{ errors.fArea }}</span></div>
    <div class="fg full"><label>Address</label><textarea id="fAddr" v-model="form.fAddr" @blur="validate('fAddr')" rows="2" placeholder="Door no, street, locality, city, pincode"></textarea></div>
   </div>
  </div>

  <div class="card"><h3><span class="stp">3</span>Walk-in Details</h3>
   <div class="fgrid">
    <div class="fg" id="fg-fWDate" :class="{'has-err':errors.fWDate,ok:touched.fWDate &amp;&amp; !errors.fWDate}"><label>Walk-in Date <span class="req">*</span></label><input type="date" id="fWDate" v-model="form.fWDate" @blur="validate('fWDate')"><span class="err" id="e-fWDate">{{ errors.fWDate }}</span></div>
    <div class="fg"><label>Walk-in Type</label><select id="fWType" v-model="form.fWType" @blur="validate('fWType')"><option>Fresh Walk-in</option><option>CC Appointment (HO assigned)</option><option>Referral</option><option>Repeat / Revisit</option><option>Camp / Event</option></select></div>
    <div class="fg"><label>Consultant Name</label><input id="fConsult" v-model="form.fConsult" @blur="validate('fConsult')" placeholder="Consulting doctor / consultant"></div>
    <div class="fg" id="fg-fWFor" :class="{'has-err':errors.fWFor,ok:touched.fWFor &amp;&amp; !errors.fWFor}"><label>Walk-in For <span class="req">*</span></label><select id="fWFor" v-model="form.fWFor" @blur="validate('fWFor')"><option value="">— select —</option><option>Consultation Only</option><option>Walk-in for Treatment (Enquiry)</option><option>Joined for Treatment</option></select><span class="err" id="e-fWFor">{{ errors.fWFor }}</span></div>
    <div class="fg"><label>Department</label><select id="fDept" v-model="form.fDept" @blur="validate('fDept')"><option>Slimming</option><option>Hair</option><option>Skin</option><option>Laser</option></select></div>
    <div class="fg lk" id="fg-fBranch" :class="{'has-err':errors.fBranch,ok:touched.fBranch &amp;&amp; !errors.fBranch}"><label>Branch <span class="req">*</span></label>
     <input id="fBranch" v-model="form.fBranch" :class="{'lk-set':links.fBranch.id}" @input="searchLink('fBranch')" @keydown="linkKey('fBranch',$event)" @click.stop @focus="links.fBranch.open=links.fBranch.rows.length>0" role="combobox" :aria-expanded="links.fBranch.open" aria-controls="dd-fBranch" autocomplete="off" @blur="validate('fBranch')" placeholder="Type to search branch...">
     <div class="lk-dd" id="dd-fBranch" :class="{show:links.fBranch.open}" role="listbox" @click.stop>
      <div v-if="links.fBranch.busy" class="empty" role="status">Searching…</div>
      <div v-else-if="links.fBranch.error" class="empty" role="alert">{{ links.fBranch.error }} <button type="button" @click="searchLink('fBranch')">Retry</button></div>
      <template v-else><div v-for="(row,index) in links.fBranch.rows" :key="row.id" class="it" :class="{hi:index===links.fBranch.selected}" role="option" :aria-selected="index===links.fBranch.selected" @mousedown.prevent="chooseLink('fBranch',row)"><b>{{ row.label }}</b><small v-if="row.sub">{{ row.sub }}</small></div>
      <div v-if="!links.fBranch.rows.length" class="empty">No match — keep typing</div></template>
     </div><span class="err" id="e-fBranch">{{ errors.fBranch }}</span></div>
   </div>
  </div>

  <div class="card"><h3><span class="stp">4</span>Booking Status & PD Form</h3>
   <div class="fgrid">
    <div class="fg" id="fg-book" :class="{'has-err':errors.book,ok:touched.book &amp;&amp; !errors.book}"><label>Booked / Unbooked <span class="req">*</span></label>
     <div class="seg" id="segBook"><button type="button" :class="{on:form.book==='Booked'}" @click="form.book='Booked';validate('book')">✓ Booked</button><button type="button" class="ub" :class="{on:form.book==='Unbooked'}" @click="form.book='Unbooked';validate('book')">Unbooked</button></div><span class="err" id="e-book">{{ errors.book }}</span></div>
    <div class="fg"><label>PD Form Number</label><input id="fPDNo" v-model="form.fPDNo" @blur="validate('fPDNo')" placeholder="e.g. PD-2026-0147"></div>
    <div class="fg full"><label>PD Form Upload</label>
     <label class="upl">📄 <span id="pdLbl">{{ pdFile ? "✓ " + pdFile.name + " attached" : "Click to upload PD form (PDF / photo)" }}</span><input type="file" id="fPD" accept=".pdf,image/*" ref="fileInput" @change="pickFile"></label></div>
   </div>
  </div>

  <div class="card"><h3><span class="stp">5</span>Consultation Handling</h3>
   <div class="fgrid">
    <div class="fg lk" id="fg-fEmp" :class="{'has-err':errors.fEmp,ok:touched.fEmp &amp;&amp; !errors.fEmp}"><label>Consultation Taken By (Practitioner) <span class="req">*</span></label>
     <input id="fEmp" v-model="form.fEmp" :class="{'lk-set':links.fEmp.id}" @input="searchLink('fEmp')" @keydown="linkKey('fEmp',$event)" @click.stop @focus="links.fEmp.open=links.fEmp.rows.length>0" role="combobox" :aria-expanded="links.fEmp.open" aria-controls="dd-fEmp" autocomplete="off" @blur="validate('fEmp')" placeholder="Type to search practitioner...">
     <div class="lk-dd" id="dd-fEmp" :class="{show:links.fEmp.open}" role="listbox" @click.stop>
      <div v-if="links.fEmp.busy" class="empty" role="status">Searching…</div>
      <div v-else-if="links.fEmp.error" class="empty" role="alert">{{ links.fEmp.error }} <button type="button" @click="searchLink('fEmp')">Retry</button></div>
      <template v-else><div v-for="(row,index) in links.fEmp.rows" :key="row.id" class="it" :class="{hi:index===links.fEmp.selected}" role="option" :aria-selected="index===links.fEmp.selected" @mousedown.prevent="chooseLink('fEmp',row)"><b>{{ row.label }}</b><small v-if="row.sub">{{ row.sub }}</small></div>
      <div v-if="!links.fEmp.rows.length" class="empty">No match — keep typing</div></template>
     </div><span class="err" id="e-fEmp">{{ errors.fEmp }}</span></div>
    <div class="fg lk" id="fg-fBM" :class="{'has-err':errors.fBM,ok:touched.fBM &amp;&amp; !errors.fBM}"><label>Branch Manager (Practitioner)</label>
     <input id="fBM" v-model="form.fBM" :class="{'lk-set':links.fBM.id}" @input="searchLink('fBM')" @keydown="linkKey('fBM',$event)" @click.stop @focus="links.fBM.open=links.fBM.rows.length>0" role="combobox" :aria-expanded="links.fBM.open" aria-controls="dd-fBM" autocomplete="off" @blur="validate('fBM')" placeholder="Type to search practitioner...">
     <div class="lk-dd" id="dd-fBM" :class="{show:links.fBM.open}" role="listbox" @click.stop>
      <div v-if="links.fBM.busy" class="empty" role="status">Searching…</div>
      <div v-else-if="links.fBM.error" class="empty" role="alert">{{ links.fBM.error }} <button type="button" @click="searchLink('fBM')">Retry</button></div>
      <template v-else><div v-for="(row,index) in links.fBM.rows" :key="row.id" class="it" :class="{hi:index===links.fBM.selected}" role="option" :aria-selected="index===links.fBM.selected" @mousedown.prevent="chooseLink('fBM',row)"><b>{{ row.label }}</b><small v-if="row.sub">{{ row.sub }}</small></div>
      <div v-if="!links.fBM.rows.length" class="empty">No match — keep typing</div></template>
     </div><span class="err" id="e-fBM">{{ errors.fBM }}</span></div>
   </div>
  </div>

  <div class="card"><h3><span class="stp">6</span>Medical Condition Risk Level <span class="pill p-b" style="margin-left:4px">Auto colour status</span></h3>
   <div class="fgrid">
    <div class="fg" id="fg-fRisk" :class="{'has-err':errors.fRisk,ok:touched.fRisk &amp;&amp; !errors.fRisk}"><label>Medical Condition Risk Level <span class="req">*</span></label>
     <select id="fRisk" v-model="form.fRisk" @blur="validate('fRisk')" @change="validate('fRisk')"><option value="">— select level —</option>
      <option>Normal</option><option>Controlled</option><option>Medical History</option><option>Active Condition</option><option>High Risk</option></select><span class="err" id="e-fRisk">{{ errors.fRisk }}</span></div>
    <div class="fg"><label>Auto Status</label><div id="riskBadge" style="padding-top:3px"><span v-if="risk" class="riskbadge" :style="{background:risk[3]}">● {{ risk[2] }} — {{ risk[0] }}</span><span v-else class="pill p-gr">Select a level</span></div></div>
    <div class="fg full"><label>Medical Notes</label><input id="fMed" v-model="form.fMed" @blur="validate('fMed')" placeholder="Condition details — e.g. controlled BP since 2023, on medication"></div>
   </div>
   <table class="risk-tbl" id="riskTbl">
    <thead><tr><th>Category</th><th>Examples</th><th>Status</th></tr></thead>
    <tbody><tr v-for="row in risks" :key="row[0]" :class="{sel:form.fRisk===row[0]}" @click="form.fRisk=row[0];validate('fRisk')" @keydown.enter="form.fRisk=row[0];validate('fRisk')" tabindex="0">
     <td style="font-weight:800"><span class="rdot" :style="{background:row[3]}"></span>{{ row[0] }}</td><td style="color:var(--mut)">{{ row[1] }}</td><td><span class="riskbadge" :style="{background:row[3]}" style="padding:3px 12px;font-size:10px">{{ row[2] }}</span></td>
    </tr></tbody>
   </table>
  </div>

  <div class="card"><h3><span class="stp">7</span>Relative in LIFE</h3>
   <div class="fgrid">
    <div class="fg" id="fg-rel" :class="{'has-err':errors.rel,ok:touched.rel &amp;&amp; !errors.rel}"><label>Any other client in LIFE is relative to client? <span class="req">*</span></label>
     <div class="seg" id="segRel"><button type="button" :class="{on:form.rel==='Yes'}" @click="form.rel='Yes';validate('rel')">Yes</button><button type="button" :class="{on:form.rel==='No'}" @click="form.rel='No';validate('rel')">No</button></div><span class="err" id="e-rel">{{ errors.rel }}</span></div>
    <div class="fg" id="relName" v-show="form.rel==='Yes'"><label>Relative Client Name</label><input id="fRelName" v-model="form.fRelName" @blur="validate('fRelName')" placeholder="Existing LIFE client name"></div>
    <div class="fg lk" id="relBr" v-show="form.rel==='Yes'"><label>Relative's Branch</label>
     <input id="fRelBr" v-model="form.fRelBr" :class="{'lk-set':links.fRelBr.id}" @input="searchLink('fRelBr')" @keydown="linkKey('fRelBr',$event)" @click.stop @focus="links.fRelBr.open=links.fRelBr.rows.length>0" role="combobox" :aria-expanded="links.fRelBr.open" aria-controls="dd-fRelBr" autocomplete="off" @blur="validate('fRelBr')" placeholder="Type to search branch..."><div class="lk-dd" id="dd-fRelBr" :class="{show:links.fRelBr.open}" role="listbox" @click.stop>
      <div v-if="links.fRelBr.busy" class="empty" role="status">Searching…</div>
      <div v-else-if="links.fRelBr.error" class="empty" role="alert">{{ links.fRelBr.error }} <button type="button" @click="searchLink('fRelBr')">Retry</button></div>
      <template v-else><div v-for="(row,index) in links.fRelBr.rows" :key="row.id" class="it" :class="{hi:index===links.fRelBr.selected}" role="option" :aria-selected="index===links.fRelBr.selected" @mousedown.prevent="chooseLink('fRelBr',row)"><b>{{ row.label }}</b><small v-if="row.sub">{{ row.sub }}</small></div>
      <div v-if="!links.fRelBr.rows.length" class="empty">No match — keep typing</div></template>
     </div></div>
   </div>
  </div>

  <div class="card" style="display:flex;gap:12px;align-items:center;flex-wrap:wrap">
   <span style="font-size:11.5px;color:var(--mut)">Registration applies to <b>both Booked and Unbooked</b> walk-ins — every client gets a LIFE Client ID.</span>
   <button class="btn btn-o" style="margin-left:auto" @click="resetForm">Clear Form</button>
   <button class="btn btn-g" @click="saveClient" :disabled="busy || !!saved">{{ busy ? "Saving…" : "✓ Register Client" }}</button>
  </div>
 </div>

 <!-- ================= RIGHT RAIL ================= -->
 <aside class="rail">
  <div class="pv" id="pvCard"><div class="av">{{ initials }}</div><div class="nm">{{ form.fName || 'New Client' }}</div>
   <div v-if="form.fAlias" class="al">alias: {{ form.fAlias }}</div><div class="meta">{{ [form.fGender,ageText,form.fArea].filter(Boolean).join(' · ') || '—' }}</div><div class="meta num">{{ form.fPhone }}</div>
   <div class="row2"><span v-if="form.book" class="pill" :class="form.book==='Booked'?'p-g':'p-gr'">{{ form.book.toUpperCase() }}</span><span v-if="form.fWFor" class="pill p-b">{{ form.fWFor.toUpperCase() }}</span><span v-if="form.fPDNo" class="pill p-a num">PD: {{ form.fPDNo }}</span></div>
   <div v-if="risk" style="margin-top:10px"><span class="riskbadge" :style="{background:risk[3]}">● {{ risk[2] }} — {{ risk[0] }}</span></div></div>
  <div class="card"><h3>Today's Registrations <span class="pill p-g num" id="regCount" style="margin-left:auto">{{ registrations.length }}</span></h3>
   <div style="overflow-x:auto"><table class="tbl"><thead><tr><th>Client</th><th>Booked</th><th>Risk</th></tr></thead><tbody id="regRows">
    <tr v-if="loading"><td colspan="3" role="status">Loading registrations…</td></tr>
    <tr v-else-if="loadError"><td colspan="3" role="alert">{{ loadError }} <button type="button" @click="loadRegistrations">Retry</button></td></tr>
    <template v-else><tr v-for="client in registrations" :key="client.name"><td><div style="font-weight:700">{{ client.patient_name || client.name }}</div><div style="font-size:10px;color:var(--mut)" class="num">{{ client.name }}</div></td><td><span class="pill" :class="client.custom_final_decision==='Booked'?'p-g':'p-gr'">{{ (client.custom_final_decision || '—').toUpperCase() }}</span></td><td><span class="rdot" :style="{background:client.custom_health_flag?.includes('Red')?'#C62828':client.custom_health_flag?.includes('Orange')?'#EF6C00':'#2E7D32'}"></span><span style="font-size:10.5px;font-weight:700">{{ client.custom_health_flag?.replace(' Flag','').toUpperCase() || '—' }}</span></td></tr>
    <tr v-if="!registrations.length"><td colspan="3" style="color:var(--mut);padding:14px">No registrations yet today.</td></tr></template>
   </tbody></table></div>
  </div>
 </aside>
</div>

<div class="ftr">LIFE SLIMMING AND COSMETIC CLINIC PVT. LTD. · Client Registration · saves to Patient (Client DocType)</div>
</fieldset>
<div class="toast" id="toast" :class="{on:toastMessage}" role="status"><span class="tk">✓</span><span id="toastMsg">{{ toastMessage }}</span></div>




</div>
</template>

<style scoped>


#cr-root{--g900:#0F3D1E;--g800:#14501F;--g700:#1B5E20;--g600:#2E7D32;--g500:#43A047;--g400:#66BB6A;--g100:#E8F5E9;--g50:#F3FAF4;
 --ink:#152418;--mut:#5F6F63;--line:#DCE9DE;--red:#C62828;--redbg:#FDECEA;--amb:#E65100;--ambbg:#FFF3E0;--blu:#1565C0;--blubg:#E3F2FD;
 --yel:#F9A825;--org:#EF6C00;--blk:#212121;
 --shadow:0 1px 2px rgba(15,61,30,.06),0 4px 14px rgba(15,61,30,.07);--disp:'Archivo',system-ui,sans-serif;--body:'Inter',system-ui,sans-serif}
*{margin:0;padding:0;box-sizing:border-box}
#cr-root{font-family:var(--body);background:var(--g50);color:var(--ink);font-size:13.5px;line-height:1.45;background-image:radial-gradient(circle at 85% -10%,rgba(67,160,71,.08),transparent 45%)}
button{font-family:inherit;cursor:pointer}
.num{font-variant-numeric:tabular-nums}
.hdr{position:sticky;top:0;z-index:60;background:linear-gradient(135deg,var(--g900),var(--g700) 70%,var(--g600));color:#fff;box-shadow:0 2px 12px rgba(15,61,30,.25)}
.hdr-in{max-width:1380px;margin:0 auto;padding:13px 24px;display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.logo{display:flex;align-items:center;gap:12px}
.logo-mark{width:40px;height:40px;border-radius:10px;background:#fff;color:var(--g700);display:flex;align-items:center;justify-content:center;font-family:var(--disp);font-weight:800;font-size:18px}
.logo h1{font-family:var(--disp);font-size:15.5px;font-weight:700;line-height:1.15}
.logo small{display:block;font-weight:500;font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#BFE3C4}
.hchip{margin-left:auto;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.22);padding:7px 15px;border-radius:99px;font-size:11.5px;font-weight:700}
.wrap{max-width:1380px;margin:0 auto;padding:18px 24px 60px;display:grid;grid-template-columns:1fr 350px;gap:16px;align-items:start}
.card{background:#fff;border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow);padding:16px 18px;margin-bottom:14px}
.card h3{font-family:var(--disp);font-size:13.5px;font-weight:800;color:var(--g900);margin-bottom:12px;display:flex;align-items:center;gap:9px}
.card h3 .stp{background:linear-gradient(135deg,var(--g600),var(--g700));color:#fff;width:24px;height:24px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:11.5px}
.fgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}
.fg{display:flex;flex-direction:column;gap:4px;position:relative}
.fg label{font-size:10px;font-weight:800;letter-spacing:1px;text-transform:uppercase;color:var(--mut)}
.fg label .req{color:var(--red)}
.fg input,.fg select,.fg textarea{border:1.5px solid var(--line);border-radius:9px;padding:9px 11px;font-family:var(--body);font-size:13px;background:#fff;color:var(--ink);outline:none;transition:border .15s}
.fg input:focus,.fg select:focus,.fg textarea:focus{border-color:var(--g500)}
.fg .hint{font-size:10px;color:var(--mut)}
.fg.full{grid-column:1/-1}
/* inline per-field error */
.fg .err{display:none;font-size:10.5px;font-weight:700;color:var(--red);margin-top:2px;line-height:1.3}
.fg.has-err .err{display:block}
.fg.has-err input,.fg.has-err select,.fg.has-err textarea{border-color:var(--red);box-shadow:0 0 0 2px rgba(198,40,40,.12)}
.fg.ok input,.fg.ok select{border-color:var(--g500)}
/* link typeahead dropdown */
.lk{position:relative}
.lk-dd{position:absolute;top:100%;left:0;right:0;z-index:80;background:#fff;border:1.5px solid var(--line);border-top:none;border-radius:0 0 10px 10px;box-shadow:0 8px 20px rgba(15,61,30,.14);max-height:240px;overflow-y:auto;display:none}
.lk-dd.show{display:block}
.lk-dd .it{padding:8px 11px;font-size:12.5px;cursor:pointer;border-bottom:1px solid #F0F5F1}
.lk-dd .it:hover,.lk-dd .it.hi{background:var(--g50)}
.lk-dd .it b{color:var(--g800)}
.lk-dd .it small{display:block;color:var(--mut);font-size:10px;font-variant-numeric:tabular-nums}
.lk-dd .empty{padding:10px 11px;font-size:11.5px;color:var(--mut)}
.lk-set{border-color:var(--g500)!important}
.seg{display:flex;gap:0;border:1.5px solid var(--line);border-radius:10px;overflow:hidden}
.seg button{flex:1;border:none;background:#fff;padding:9px 6px;font-weight:800;font-size:12px;color:var(--mut);transition:all .15s}
.seg button.on{background:linear-gradient(135deg,var(--g600),var(--g700));color:#fff}
.seg button.on.ub{background:linear-gradient(135deg,#78909C,#546E7A)}
.risk-tbl{width:100%;border-collapse:collapse;font-size:11.5px;margin-top:8px}
.risk-tbl th{background:var(--g50);text-align:left;padding:7px 9px;font-size:9.5px;letter-spacing:1px;text-transform:uppercase;font-weight:800;color:var(--g800);border-bottom:2px solid var(--line)}
.risk-tbl td{padding:7px 9px;border-bottom:1px solid #EEF4EF}
.risk-tbl tr{cursor:pointer;transition:background .12s}
.risk-tbl tr:hover td{background:var(--g50)}
.risk-tbl tr.sel td{background:var(--g100)}
.rdot{display:inline-block;width:12px;height:12px;border-radius:50%;margin-right:7px;vertical-align:-1px}
.riskbadge{display:inline-flex;align-items:center;gap:8px;border-radius:99px;padding:7px 16px;font-weight:800;font-size:12px;font-family:var(--disp);color:#fff;letter-spacing:.4px}
.upl{border:2px dashed var(--g400);border-radius:11px;padding:14px;text-align:center;background:var(--g50);cursor:pointer;transition:all .15s;font-size:12px;color:var(--g700);font-weight:700}
.upl:hover{background:var(--g100)}
.upl input{display:none}
.btn{border:none;border-radius:10px;padding:12px 24px;font-weight:800;font-size:13.5px;transition:transform .12s}
.btn:hover{transform:translateY(-1px)}
.btn-g{background:linear-gradient(135deg,var(--g600),var(--g700));color:#fff;box-shadow:0 3px 10px rgba(27,94,32,.3)}
.btn-o{background:#fff;color:var(--g700);border:1.5px solid var(--g500)}
.btn-sm{padding:6px 13px;font-size:11.5px;border-radius:8px}
.rail{position:sticky;top:80px}
.pv{background:linear-gradient(160deg,#fff,var(--g50));border:1px solid var(--line);border-radius:16px;box-shadow:var(--shadow);padding:18px;text-align:center;margin-bottom:14px;position:relative;overflow:hidden}
.pv::before{content:"";position:absolute;top:0;left:0;right:0;height:5px;background:linear-gradient(90deg,var(--g500),var(--g700))}
.pv .av{width:66px;height:66px;border-radius:50%;background:linear-gradient(135deg,var(--g600),var(--g800));color:#fff;font-family:var(--disp);font-weight:800;font-size:24px;display:flex;align-items:center;justify-content:center;margin:4px auto 8px}
.pv .nm{font-family:var(--disp);font-weight:800;font-size:17px;color:var(--g900)}
.pv .al{font-size:11px;color:var(--mut)}
.pv .meta{font-size:11.5px;color:var(--mut);margin-top:3px}
.pv .row2{display:flex;justify-content:center;gap:8px;margin-top:10px;flex-wrap:wrap}
.pill{display:inline-block;padding:4px 11px;border-radius:99px;font-size:10px;font-weight:800;letter-spacing:.4px}
.p-g{background:var(--g100);color:var(--g800)}.p-r{background:var(--redbg);color:var(--red)}.p-a{background:var(--ambbg);color:var(--amb)}.p-b{background:var(--blubg);color:var(--blu)}.p-gr{background:#ECEFF1;color:#546E7A}
.tbl{width:100%;border-collapse:collapse;font-size:12px}
.tbl th{background:var(--g50);color:var(--g800);text-align:left;padding:8px 9px;font-size:9.5px;letter-spacing:.9px;text-transform:uppercase;font-weight:800;border-bottom:2px solid var(--line)}
.tbl td{padding:8px 9px;border-bottom:1px solid #EEF4EF;vertical-align:middle}
.toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%) translateY(80px);background:var(--g900);color:#fff;padding:12px 22px;border-radius:11px;font-weight:600;font-size:13px;z-index:400;opacity:0;transition:all .3s;display:flex;gap:10px}
.toast.on{opacity:1;transform:translateX(-50%)}
.toast .tk{color:#7CF29A;font-weight:800}
.ftr{max-width:1380px;margin:0 auto;padding:0 24px 26px;text-align:center;font-size:11px;color:var(--mut)}
@media (max-width:980px){.wrap{grid-template-columns:1fr}.rail{position:static}}


.registration-fields{border:0;min-width:0;padding:0;margin:0}.registration-error,.registration-success{padding:12px 24px}.registration-error{color:var(--red);background:var(--redbg)}
@media(max-width:480px){.wrap{padding:12px 10px 32px}.fgrid{grid-template-columns:minmax(0,1fr)}.fg,.card,.rail{min-width:0}.risk-tbl td,.risk-tbl th{padding:6px 4px}.riskbadge{white-space:normal}.btn{padding:10px 14px}}

</style>
