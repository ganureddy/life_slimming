<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { request } from '../../api/http';
import { apiUrl } from '../../api/config';
import { leaderboard, rank, changes, kinds, sortedAgents, highlights, waitingLeads, WEEKLY_TARGET } from '../../lib/cc-live-tv';
const root = ref(null), data = ref(null), error = ref(''), clock = ref(new Date()), sound = ref(false), soundError = ref('');
const feed = ref([]), active = ref(null), scale = ref(1), lastUpdated = ref(null);
const volume = ref(1), lastActivity = ref(Date.now());
const idle = computed(() => !active.value && clock.value.getTime() - lastActivity.value > 40000);
const roster = computed(() => sortedAgents(agents.value, 'today'));
const waiting = computed(() => error.value || stale.value ? [] : waitingLeads(data.value, lastUpdated.value ? clock.value-lastUpdated.value : 0));
const rosterSize = computed(() => waiting.value.length ? 6 : 8);
const rosterPage = computed(() => Math.floor(Math.max(0, clock.value.getTime()-lastActivity.value-40000)/8000) % Math.max(1, Math.ceil(roster.value.length/rosterSize.value)));
const rosterRows = computed(() => roster.value.slice(rosterPage.value*rosterSize.value, (rosterPage.value+1)*rosterSize.value));
const weekly = computed(() => sortedAgents(agents.value, 'week'));
const headlines = computed(() => highlights(agents.value));
const weeklyPercent = agent => Math.min(100, Math.round(agent.week.walkins/WEEKLY_TARGET*100));
const agents = computed(() => data.value ? leaderboard(data.value) : []);
const totals = computed(() => agents.value.reduce((sum, agent) => { for (const key in sum) sum[key] += agent.today[key]; return sum; }, {leads:0, booked:0, walkins:0, visitedBooked:0, visitStatus:0}));
const latest = computed(() => data.value?.rows.slice().sort((a,b) => b.creation.localeCompare(a.creation))[0]);
const zone = computed(() => data.value?.timezone || 'Asia/Kolkata');
const timeText = computed(() => clock.value.toLocaleTimeString('en-IN', { timeZone: zone.value, hour:'2-digit', minute:'2-digit' }));
const dateText = computed(() => clock.value.toLocaleDateString('en-IN', { timeZone: zone.value, weekday:'long', day:'numeric', month:'short', year:'numeric' }));
const stale = computed(() => !lastUpdated.value || clock.value - lastUpdated.value > 15000);
const failedImages = ref(new Set());
function agentImage(id) {
  const path = data.value?.agent_images?.[id];
  if (!path) return '';
  const url = path.startsWith('/') && !path.startsWith('//') ? apiUrl(path) : path;
  return failedImages.value.has(url) ? '' : url;
}
function imageFailed(event) { failedImages.value.add(event.target.getAttribute('src')); }
const initials = name => name.split(/\s+/).slice(0,2).map(word => word[0]).join('');
function podium(period) { const rows = rank(agents.value, period); return (period === 'today' ? [1,0,2] : [0,1,2]).map(index => ({agent: rows[index], rank:index+1})); }
let stopped = false, pollTimer, clockTimer, alertTimer, controller, audio, observer;
const queue = [];
let lastWaitingAlarm = 0;
function tick() {
  clock.value = new Date();
  if (waiting.value.length && !active.value && sound.value && clock.value.getTime()-lastWaitingAlarm >= 120000) {
    lastWaitingAlarm = clock.value.getTime();
    [1047,1047,1047,1397].forEach((frequency,index) => tone(frequency,index*.22,.6));
  }
}
async function poll() {
  controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 20000);
  try {
    const response = await request('life_slimming.api.cc_live_tv.snapshot', {signal:controller.signal});
    if (stopped) return;
    const next = response.message;
    if (!next || !Array.isArray(next.rows) || !next.today || !next.agents) throw new Error('Invalid TV response. Retrying…');
    const events = changes(data.value, next);
    const oldWinner = rank(agents.value, 'today')[0];
    if (data.value?.today !== next.today) { feed.value = []; queue.length = 0; active.value = null; clearTimeout(alertTimer); }
    const visibleEvent = event => !event.agentId || Object.hasOwn(next.agents, event.agentId);
    feed.value = feed.value.filter(visibleEvent);
    for (let i = queue.length - 1; i >= 0; i--) if (!visibleEvent(queue[i])) queue.splice(i, 1);
    if (active.value && !visibleEvent(active.value)) { active.value = null; clearTimeout(alertTimer); }
    if (events.length) lastActivity.value = Date.now();
    data.value = next;
    const winner = rank(agents.value, 'today')[0];
    feed.value = [...events.slice().reverse(), ...feed.value].slice(0,7);
    queue.push(...events);
    if (events.some(event => event.type === 'walkin') && oldWinner && winner && oldWinner.id !== winner.id) queue.push({id:`champ:${next.timestamp}`,type:'champ',agent:winner.name,agentId:winner.id,client:'#1 Agent of the Day',time:next.timestamp});
    // Avoid minutes of stale announcements after a reconnect or a bulk import.
    if (queue.length > 12) queue.splice(0, queue.length - 12);
    nextAlert(); error.value = ''; lastUpdated.value = new Date();
  } catch (err) {
    if (!stopped && [401,403].includes(err.status)) { data.value = null; feed.value = []; queue.length = 0; active.value = null; clearTimeout(alertTimer); }
    if (!stopped) error.value = err.name === 'AbortError' ? 'Connection timed out. Retrying…' : err.message;
  } finally {
    clearTimeout(timeout);
    if (!stopped) pollTimer = setTimeout(poll, 5000);
  }
}
function tone(frequency, delay, duration = 1) {
  if (!sound.value || audio?.state !== 'running') return;
  const start = audio.currentTime + delay;
  const oscillator = audio.createOscillator(), gain = audio.createGain();
  oscillator.frequency.value = frequency;
  gain.gain.setValueAtTime(0.0001, start);
  gain.gain.exponentialRampToValueAtTime(Math.max(0.0001, 0.16 * volume.value), start + 0.025);
  gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);
  oscillator.connect(gain); gain.connect(audio.destination);
  oscillator.start(start); oscillator.stop(start + duration + 0.05);
  oscillator.onended = () => { oscillator.disconnect(); gain.disconnect(); };
}
function play(type) {
  const notes = {lead:[784,784],booked:[523,659,784],walkin:[523,659,784,1047],champ:[523,659,784,1047,784,1047,1319]}[type];
  notes.forEach((frequency,index) => {
    const delay = index * (type === 'lead' ? .6 : .18);
    tone(frequency, delay, type === 'lead' ? 3 : 1.2);
    tone(frequency * 2, delay, .5);
  });
}
async function toggleSound() {
  soundError.value = '';
  try {
    if (sound.value) { sound.value = false; await audio.suspend(); return; }
    const Audio = window.AudioContext || window.webkitAudioContext;
    if (!Audio) throw new Error('Sound is unavailable in this browser.');
    audio ||= new Audio();
    await audio.resume(); sound.value = audio.state === 'running';
    if (!sound.value) throw new Error('Click again to enable sound.');
    tone(880,0,0.3);
  } catch (err) { sound.value = false; soundError.value = err.message; }
}
function nextAlert() {
  if (active.value || !queue.length || stopped) return;
  active.value = queue.shift(); play(active.value.type);
  alertTimer = setTimeout(dismiss, ['champ','booked'].includes(active.value.type) ? 8000 : 6500);
}
function dismiss() { lastActivity.value = Date.now(); clearTimeout(alertTimer); active.value = null; alertTimer = setTimeout(nextAlert,400); }
async function fullscreen() {
  try { if (document.fullscreenElement) await document.exitFullscreen(); else await root.value.requestFullscreen(); }
  catch { soundError.value = 'Fullscreen is unavailable. Use your browser fullscreen control.'; }
}
function keydown(event) {
  if (event.ctrlKey || event.metaKey || event.altKey || event.repeat || ['INPUT','TEXTAREA'].includes(event.target?.tagName)) return;
  if (event.key.toLowerCase() === 'f') fullscreen();
  if (event.key.toLowerCase() === 'm') toggleSound();
}
onMounted(() => {
  observer = new ResizeObserver(([entry]) => { scale.value = Math.min(entry.contentRect.width / 1920, entry.contentRect.height / 1080); });
  observer.observe(root.value);
  document.addEventListener('keydown',keydown);
  clockTimer = setInterval(tick,1000);
  poll();
});
onUnmounted(() => {
  stopped = true; controller?.abort(); observer?.disconnect();
  clearTimeout(pollTimer); clearTimeout(alertTimer); clearInterval(clockTimer);
  document.removeEventListener('keydown',keydown); audio?.close().catch(() => {});
});
</script>

<template>
  <div ref="root" class="cc-tv">
    <div class="tv-stage" :style="{transform:`translate(-50%, -50%) scale(${scale})`}">
      <header><div class="logo">L</div><h1>LIFE CALL CENTRE<small>COMMAND · LIVE LEADERBOARD</small></h1><div class="live" :class="{offline:error || stale}"><i></i>{{ error || stale ? 'CONNECTING' : 'LIVE' }}</div>
        <div class="chips"><div v-for="(label,key) in {leads:'LEADS TODAY',booked:'APPOINTMENT BOOKED',walkins:'VISITED',visitedBooked:'VISITED BOOKED',visitStatus:'VISIT STATUS'}" :key="key" class="chip"><b>{{ data ? totals[key] : '—' }}</b><span>{{ label }}</span></div></div>
        <div class="sound-controls"><button :aria-pressed="sound" aria-label="Toggle sound (M)" @click="toggleSound">{{ sound ? '🔊' : '🔇' }}</button><input v-model.number="volume" type="range" min="0" max="1" step="0.05" aria-label="Alert volume"></div>
        <div class="clock">{{ timeText }}<small>{{ dateText }}</small></div>
      </header>
      <main><section><template v-for="period in ['today','month']" :key="period">
        <div class="sec" :class="{'month-heading':period==='month'}">{{ period === 'today' ? '⭐ TODAY’S TOP 3 · VISITED' : '🏆 THIS MONTH TOP 3 · 6TH–5TH' }}</div>
        <div class="pod" :class="{m:period==='month'}">
          <template v-for="slot in podium(period)" :key="slot.rank"><article v-if="slot.agent" class="ag" :class="`r${slot.rank}`">
            <div v-if="slot.rank===1" class="crown">👑</div><div class="rank">#{{ slot.rank }}</div>
            <div class="ph"><img v-if="agentImage(slot.agent.id)" :key="agentImage(slot.agent.id)" :src="agentImage(slot.agent.id)" :alt="slot.agent.name" @error="imageFailed"><span v-else>{{ initials(slot.agent.name) }}</span></div><div class="nm">{{ slot.agent.name }}</div><div class="br">📍 {{ slot.agent.branch || 'Branch not assigned' }}</div>
            <div class="st"><div v-for="(label,key) in {walkins:'VISITED',visitedBooked:'VISITED BOOKED',booked:'APPOINTMENT BOOKED',leads:'LEADS',visitStatus:'VISIT STATUS'}" :key="key"><b>{{ slot.agent[period][key] }}</b><span>{{ label }}</span></div></div>
          </article><article v-else class="ag empty">{{ data ? 'No ranked activity yet' : 'Loading live data…' }}</article></template>
        </div>
      </template></section>
      <section class="right">
        <div v-if="waiting.length" class="waiting" role="status"><b>⚠ LEAD WAITING · NO CALL RECORDED</b><h4>{{ waiting[0].lead_name || waiting[0].name }}</h4><p>{{ data.agents[waiting[0].lead_owner] || 'Unassigned' }} · {{ waiting[0].minutes }} min<span v-if="waiting.length>1"> · +{{ waiting.length-1 }} more</span></p><p class="visit-status">Visit Status: {{ waiting[0].custom_visit_status || 'Not set' }}</p></div>
        <div class="pane-wrap">
          <div v-if="!idle" class="pane">
            <div class="sec">🔔 LATEST LEAD</div><div class="latest"><div class="bell">🔔</div><div><small>LATEST LEAD RECEIVED</small><h3>{{ latest?.lead_name || 'Waiting for leads…' }}</h3><p v-if="latest">{{ data.agents[latest.lead_owner] || 'Unassigned' }} · {{ latest.source }} · {{ latest.branch || latest.lead_assign_to_branch }}</p><p v-if="latest" class="visit-status">Visit Status: {{ latest.custom_visit_status || 'Not set' }}</p></div></div>
            <div class="sec">LIVE ACTIVITY</div><div class="feed"><div v-for="event in feed" :key="event.id" class="ev" :style="{'--k':kinds[event.type].color}"><div class="ic">{{ kinds[event.type].icon }}</div><div><b>{{ kinds[event.type].title }} · {{ event.client }}</b><span>{{ event.agent }} · {{ event.branch }}</span><span class="visit-status">Visit Status: {{ event.visitStatus || 'Not set' }}</span></div><em>{{ event.time.slice(11,16) }}</em></div><p v-if="!feed.length" class="empty">New activity will appear here while this screen is open.</p></div>
          </div>
          <div v-else class="pane roster"><div class="sec">👥 AGENT RANKINGS · TODAY</div><div class="rh"><span>#</span><span></span><span>AGENT</span><span>VISIT</span><span>V.BKD</span><span>APPT</span><span>LEADS</span><span>VISIT<br>STATUS</span></div>
            <div class="roster-list"><div v-for="(agent,index) in rosterRows" :key="agent.id" class="rw" :class="`r${rosterPage*rosterSize+index+1}`"><b class="rk">{{ rosterPage*rosterSize+index+1 }}</b><div class="ph"><img v-if="agentImage(agent.id)" :src="agentImage(agent.id)" :alt="agent.name" @error="imageFailed"><span v-else>{{ initials(agent.name) }}</span></div><div class="rn" :title="agent.name">{{ agent.name }}<small>{{ agent.branch || 'Branch not assigned' }}</small></div><div v-for="key in ['walkins','visitedBooked','booked','leads','visitStatus']" :key="key" class="v">{{ agent.today[key] }}</div></div></div>
            <p v-if="!roster.length" class="empty">No agent activity yet.</p><small v-else class="page-label">{{ rosterPage+1 }} / {{ Math.ceil(roster.length/rosterSize) }}</small>
          </div>
        </div>
      </section></main>
      <section class="weekly-band" aria-label="Weekly ranking"><div class="tag">WEEKLY RANKING<small>TARGET {{ WEEKLY_TARGET }} VISITS / WEEK · MON–SUN</small></div><div class="mq"><div v-if="weekly.length" class="marquee-track"><div v-for="copy in 2" :key="copy" class="marquee-copy" :aria-hidden="copy===2"><span v-for="(agent,index) in weekly" :key="agent.id" class="wi"><b>#{{ index+1 }}</b><div class="ph"><img v-if="agentImage(agent.id)" :src="agentImage(agent.id)" :alt="agent.name" @error="imageFailed"><span v-else>{{ initials(agent.name) }}</span></div><b>{{ agent.name }}</b><span class="bar"><i :style="{width:`${weeklyPercent(agent)}%`}"></i></span><span>{{ agent.week.walkins }} / {{ WEEKLY_TARGET }} · {{ weeklyPercent(agent) }}%</span><span class="weekly-status">Visit Status: {{ agent.week.visitStatus }}</span></span></div></div><p v-else class="empty">Waiting for weekly activity…</p></div></section>
      <section class="breaking-band" aria-label="Team highlights"><div class="tag">BREAKING</div><div class="mq"><div class="marquee-track"><div v-for="copy in 2" :key="copy" class="marquee-copy" :aria-hidden="copy===2"><span v-for="line in headlines" :key="line">{{ line }} <em> ● </em></span></div></div></div></section>
      <div v-if="active" class="overlay" :style="{'--oc':kinds[active.type].color}"><div><div v-if="active.type==='champ'" class="ph"><img v-if="agentImage(active.agentId)" :src="agentImage(active.agentId)" :alt="active.agent" @error="imageFailed"><span v-else>{{ initials(active.agent) }}</span></div><div v-else class="ico">{{ kinds[active.type].icon }}</div><div class="big">{{ kinds[active.type].title }}</div><h2>{{ active.client }}</h2><p>{{ active.agent }} {{ active.branch ? ' · '+active.branch : '' }}</p><p v-if="active.type==='champ'" class="visit-status">Visit Status: {{ agents.find(agent => agent.id===active.agentId)?.today.visitStatus || 0 }}</p><p v-if="active.type!=='champ'" class="visit-status">Visit Status: {{ active.visitStatus || 'Not set' }}</p><p v-if="active.type==='lead'">{{ [active.source,active.treatment].filter(Boolean).join(' · ') }} · CALL NOW!</p><button @click="dismiss">Dismiss</button></div>
        <div v-if="['booked','walkin','champ'].includes(active.type)" class="confetti" aria-hidden="true"><i v-for="n in 65" :key="n" :style="{left:`${(n*37)%100}%`,animationDelay:`${(n%11)*.13}s`,background:['#f5c542','#2ecc71','#4da3ff','#ff6b9d'][n%4]}" /></div>
      </div>
      <footer><span role="status">{{ error || (data ? (data.restricted_to_owner ? 'Your assigned leads' : 'All CC leads') + ' · Refreshes every 5 seconds · Visits by appointment date' : 'Connecting to live data…') }}<template v-if="lastUpdated"> · Updated {{ lastUpdated.toLocaleTimeString('en-IN', {timeZone:zone}) }}</template></span><span role="status">{{ soundError }}</span><RouterLink :to="{name:'leads-native'}">Dashboard</RouterLink><button @click="fullscreen">⛶ Fullscreen</button><button :aria-pressed="sound" @click="toggleSound">{{ sound ? '🔊 Sound on' : '🔇 Enable sound' }}</button></footer>
    </div>
  </div>
</template>

<style scoped>

.cc-tv{--bg:#06150e;--gold:#f5c542;--gold2:#ffdf8a;--ink:#f4f1e6;--mut:#9db8a8;--red:#e11d2e;--blue:#4da3ff;--card:rgba(255,255,255,.06)}
*{box-sizing:border-box;margin:0}
.cc-tv{height:100%;overflow:hidden;background:#000;font-family:"Segoe UI",Inter,system-ui,sans-serif;color:var(--ink)}
.tv-stage{position:absolute;left:0;top:0;width:1920px;height:1080px;transform-origin:0 0;background:radial-gradient(1200px 700px at 20% 0,#14573a 0,transparent 60%),radial-gradient(900px 600px at 100% 100%,#0d3b5a55 0,transparent 60%),var(--bg)}
.tv-stage:before{content:"";position:absolute;inset:8px;border:4px solid transparent;border-radius:26px;background:linear-gradient(135deg,#fff3b0,#c58f10 25%,#ffe27a 50%,#a8740a 75%,#fff3b0) border-box;-webkit-mask:linear-gradient(#000 0 0) padding-box,linear-gradient(#000 0 0);-webkit-mask-composite:xor;mask-composite:exclude;z-index:40;pointer-events:none;box-shadow:0 0 40px #f5c54255}
.tv-stage:after{content:"";position:absolute;inset:20px;border:1.5px solid #f5c54277;border-radius:16px;z-index:40;pointer-events:none}
header{height:100px;display:flex;align-items:center;gap:22px;padding:14px 56px 0;border-bottom:2px solid #ffffff14}
.logo{width:58px;height:58px;border-radius:15px;background:linear-gradient(135deg,var(--gold),#c58f10);color:#2b1d00;font:800 38px Georgia,serif;display:grid;place-items:center}
h1{font:700 30px Georgia,serif;letter-spacing:3px}h1 small{display:block;font:600 14px "Segoe UI";letter-spacing:3px;color:var(--mut)}
.live{display:flex;align-items:center;gap:8px;font-weight:800;letter-spacing:4px;color:#ff5a5a}.live i{width:13px;height:13px;border-radius:50%;background:#ff5a5a;animation:blink 1.2s infinite}
.chips{margin-left:auto;display:flex;gap:14px}.chip{background:var(--card);border:1px solid #ffffff1a;border-radius:14px;padding:6px 20px;text-align:center;min-width:130px}.chip b{display:block;font:600 40px Georgia,serif;color:var(--gold2)}.chip span{font-size:12px;letter-spacing:3px;color:var(--mut)}
.clock{font:500 44px Georgia,serif;text-align:right;min-width:190px}.clock small{display:block;font:14px "Segoe UI";color:var(--mut);letter-spacing:1px}
main{display:grid;grid-template-columns:1180px 1fr;gap:26px;padding:16px 56px 0;height:770px}
.sec{font:700 20px Georgia,serif;letter-spacing:6px;color:var(--gold);margin-bottom:10px;display:flex;align-items:center;gap:12px}.sec:after{content:"";flex:1;height:2px;background:linear-gradient(90deg,#f5c54266,transparent)}
.pod{display:grid;grid-template-columns:1fr 1.15fr 1fr;gap:18px;align-items:end;height:392px;padding-top:30px}
.pod.m{height:238px;grid-template-columns:1fr 1fr 1fr;align-items:stretch;padding-top:26px}
.ag{position:relative;background:linear-gradient(180deg,#ffffff10,#ffffff05);border:1px solid #ffffff1f;border-radius:24px;padding:14px 10px 12px;text-align:center;display:flex;flex-direction:column;align-items:center;justify-content:flex-end}
.ag.r1{height:100%;border-color:var(--gold);box-shadow:0 0 44px #f5c54255,inset 0 0 40px #f5c54218;background:linear-gradient(180deg,#f5c54222,#ffffff06)}
.ag.r2{height:88%}.ag.r3{height:80%}.pod.m .ag{height:100%!important}
.ph{width:118px;height:118px;border-radius:50%;border:5px solid var(--c,#9db8a8);background:#123 center/cover;display:grid;place-items:center;font:800 44px Georgia,serif;color:#fff;box-shadow:0 8px 24px #0008;flex:none}
.r1{--c:var(--gold)}.r1 .ph{width:160px;height:160px;font-size:60px}.r2{--c:#d6dde3}.r3{--c:#d9945a}.pod.m .ph,.pod.m .r1 .ph{width:78px;height:78px;font-size:30px;border-width:4px}
.crown{position:absolute;top:-32px;font-size:54px;animation:float 2s ease-in-out infinite}
.rank{position:absolute;top:8px;left:14px;font:900 40px Georgia,serif;color:var(--c)}.pod.m .rank{font-size:28px}
.nm{font:700 26px Georgia,serif;margin-top:8px}.r1 .nm{font-size:32px}.pod.m .nm{font-size:21px;margin-top:4px}
.br{color:var(--mut);font-size:15px}
.st{display:flex;gap:7px;margin-top:8px}.st div{background:#0007;border-radius:10px;padding:4px 9px;min-width:68px}.st b{font:600 30px Georgia,serif;display:block;color:var(--gold2)}.st span{font-size:10px;letter-spacing:1.5px;color:var(--mut);display:block;line-height:1.1}
.pod.m .st b{font-size:22px}.pod.m .st div{padding:3px 6px;min-width:58px}
.pop{animation:pop .9s}
.right{position:relative;min-height:0;display:flex;flex-direction:column}.pw{position:relative;flex:1;min-height:0}
.pane{position:absolute;inset:0;display:flex;flex-direction:column;gap:12px;transition:opacity .8s}
.latest{border-radius:22px;padding:18px 22px;background:linear-gradient(135deg,#7a5200,#c58f10);color:#fff;display:flex;gap:18px;align-items:center;min-height:150px;box-shadow:0 0 36px #f5c54244}
.latest .bell{font-size:68px;animation:ring 1.6s infinite;transform-origin:50% 10%}.latest small{letter-spacing:4px;font-weight:800;opacity:.85}.latest h3{font:700 34px Georgia,serif;line-height:1.1}.latest p{font-size:18px}
.feed{flex:1;overflow:hidden;display:flex;flex-direction:column;gap:9px}
.ev{display:flex;gap:14px;align-items:center;padding:11px 16px;border-radius:16px;background:var(--card);border-left:7px solid var(--k);animation:slide .6s}
.ev .ic{font-size:32px}.ev b{font-size:21px;display:block}.ev span{color:var(--mut);font-size:16px}.ev .visit-status{display:block;font-size:14px}.ev em{margin-left:auto;font-style:normal;color:var(--mut);font-size:15px}
.rh,.rw{display:grid;grid-template-columns:46px 56px 1fr 52px 52px 52px 52px;align-items:center;gap:6px}
.rh{font-size:11px;letter-spacing:1.5px;color:var(--mut);text-align:center;padding:0 12px}.rh i:nth-child(3){text-align:left}
.rw{background:var(--card);border-radius:14px;padding:6px 12px;height:60px;border-left:5px solid transparent;animation:slide .5s}
.rw .rk{font:800 24px Georgia,serif;color:var(--gold)}.rw .ph{width:48px;height:48px;font-size:18px;border-width:3px}
.rw .rn{font-size:19px;font-weight:600;line-height:1.1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.rw .rn small{display:block;font-size:13px;color:var(--mut);font-weight:400}
.rw .v{text-align:center;font:600 24px Georgia,serif}.rw .v:nth-of-type(1){color:var(--gold2)}
.weekly-band{position:absolute;left:56px;right:56px;top:884px;height:96px;display:flex;align-items:center;border-radius:18px;background:linear-gradient(90deg,#0c2d1f,#123f2b);border:1.5px solid #f5c54288;overflow:hidden}
.tag{flex:none;height:100%;padding:0 26px;display:flex;flex-direction:column;justify-content:center;background:linear-gradient(135deg,var(--gold),#b8800c);color:#2b1d00;font:800 22px Georgia,serif;letter-spacing:2px;z-index:2}.tag small{font:700 13px "Segoe UI";letter-spacing:1px}
.mq{flex:1;overflow:hidden;white-space:nowrap}.mq>div{display:inline-block;animation:mq 60s linear infinite;padding-left:40px}
.wi{display:inline-flex;align-items:center;gap:12px;margin-right:40px;vertical-align:middle}
.wi .ph{width:56px;height:56px;font-size:20px;border-width:3px}.wi b{font-size:22px}.wi .bar{width:120px;height:12px;border-radius:8px;background:#ffffff22;overflow:hidden}.wi .bar i{display:block;height:100%;background:linear-gradient(90deg,#2ecc71,var(--gold))}.wi span{font:600 21px Georgia,serif;color:var(--gold2)}
.breaking-band{position:absolute;left:56px;right:56px;top:988px;height:56px;display:flex;align-items:center;border-radius:12px;background:#1a0508;border:1.5px solid #e11d2e;overflow:hidden}
.breaking-band .tag{background:var(--red);color:#fff;font-size:24px;letter-spacing:4px;flex-direction:row;align-items:center;gap:10px}.breaking-band .tag:before{content:"";width:12px;height:12px;border-radius:50%;background:#fff;animation:blink 1s infinite}
.breaking-band .mq{font:700 26px "Segoe UI";letter-spacing:1px}.breaking-band .mq>div{animation-duration:40s}.breaking-band em{font-style:normal;color:var(--gold2);margin:0 6px}.breaking-band s{text-decoration:none;color:#ff8a8a;margin:0 26px}
@keyframes wpulse{50%{box-shadow:0 0 60px #ff4d4dcc}}
.sound-controls{display:flex;align-items:center;gap:6px;opacity:.85}.sound-controls button{background:#ffffff18;border:1px solid #fff3;border-radius:8px;color:#fff;font-size:15px;padding:2px 7px;cursor:pointer}.sound-controls input{width:62px;accent-color:#f5c542}
@keyframes blink{50%{opacity:.2}}@keyframes float{50%{transform:translateY(-10px)}}@keyframes mq{to{transform:translateX(-50%)}}
@keyframes ring{0%,50%,100%{transform:rotate(0)}10%{transform:rotate(22deg)}20%{transform:rotate(-20deg)}30%{transform:rotate(16deg)}40%{transform:rotate(-12deg)}}
@keyframes pop{0%{transform:scale(.85)}50%{transform:scale(1.07)}100%{transform:scale(1)}}
@keyframes slide{from{transform:translateX(60px);opacity:0}}@keyframes fade{from{opacity:0}}@keyframes zoom{from{transform:scale(.3);opacity:0}}
.cc-tv{position:fixed;inset:0;z-index:1100;width:100vw;height:100dvh;background:#000}
.tv-stage{left:50%;top:50%;transform-origin:center}
header{gap:16px}.logo{flex-shrink:0}h1{font-size:26px;letter-spacing:2px;flex-shrink:0}h1 small{font-size:12px;letter-spacing:2px}
.chips{gap:10px}.cc-tv .chip{min-width:120px;height:72px;padding:5px 10px}.cc-tv .chip b{font:600 36px/1.1 Georgia,serif}.cc-tv .chip span{line-height:1.15}.chip span{display:block;max-width:130px;letter-spacing:1.5px;font-size:11px}.live{letter-spacing:2px;font-size:14px}.live.offline,.live.offline i{color:#ffdf8a}.live.offline i{background:#ffdf8a}.clock{min-width:175px;font-size:38px}.clock small{text-transform:uppercase;font-size:12px}
main>section{min-width:0}.month-heading{margin-top:12px}.ph{overflow:hidden}.ph img{width:100%;height:100%;object-fit:cover;display:block;min-height:0}
.nm{max-width:100%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.r1 .nm{font-size:28px}.pod.m .nm{font-size:20px}.br{max-width:100%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.st{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));width:100%;gap:6px}.st div,.pod.m .st div{min-width:0;padding:4px}.st span{min-height:24px;font-size:10px;letter-spacing:1px;line-height:1.2}
.pane-wrap{position:relative;flex:1;min-height:0}.pane{gap:10px}.roster-list{display:flex;flex-direction:column;gap:7px}.rh,.rw{grid-template-columns:32px 48px minmax(0,1fr) repeat(5,43px);gap:5px}.rw{flex-shrink:0;height:57px;padding:5px 8px}.rw .ph{width:44px;height:44px}.rw .rn{font-size:17px}.rw .v{font-size:22px}.rh{padding:0 8px;font-size:10px;letter-spacing:0}.rw.r1{border-color:var(--gold);background:#f5c54222}.rw.r2{border-color:#d6dde3}.rw.r3{border-color:#d9945a}.page-label{color:var(--mut);text-align:right}
.waiting{flex:none;margin-bottom:12px;padding:10px 16px;background:linear-gradient(135deg,#8b0010,#e11d2e);border:2px solid #ffd0d0;border-radius:16px;animation:wpulse 2s infinite}.waiting b{font-size:13px;letter-spacing:1px}.waiting h4{font:700 24px Georgia,serif;margin:4px 0}.waiting p{font-size:16px}
.latest h3{overflow-wrap:anywhere}.latest small{font-size:11px;letter-spacing:2px}.ev b{font-size:18px}.ev span{font-size:14px}.empty{color:var(--mut);text-align:center;padding:20px}
.mq>.marquee-track{display:flex;width:max-content;padding-left:0;animation:mq 60s linear infinite}.marquee-copy{display:flex;align-items:center;flex-shrink:0;min-width:1808px;padding-left:40px}.breaking-band .marquee-track{animation-duration:40s}.breaking-band .marquee-copy{gap:24px}.breaking-band em{margin:0 20px}.tag small{font-size:11px;letter-spacing:0}.wi .ph{flex-shrink:0}
footer{position:absolute;left:56px;right:56px;bottom:20px;height:14px;display:flex;align-items:center;gap:12px;font-size:11px;color:var(--mut);z-index:41}footer>span:first-child{margin-right:auto;max-width:1120px}button,footer a{border:1px solid #fff4;background:#ffffff18;color:white;border-radius:7px;padding:3px 8px;cursor:pointer;white-space:nowrap;font:inherit}
.overlay .ph{width:230px;height:230px;margin:0 auto 16px;font-size:80px;border-color:var(--gold)}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}.confetti{display:none}.mq{overflow-x:auto}.marquee-copy[aria-hidden="true"]{display:none}}

.overlay{position:absolute;inset:0;display:grid;place-items:center;text-align:center;z-index:20;background:radial-gradient(circle,color-mix(in srgb,var(--oc) 35%,#06150e),#020a06 75%)}
.overlay .big{font:900 110px/1.1 'Segoe UI',sans-serif;color:var(--oc);max-width:1800px}.overlay .ico{font-size:220px;animation:ring 1.6s infinite}.overlay h2{font-size:70px;max-width:1700px;overflow-wrap:anywhere}.overlay p{font-size:42px;color:var(--gold2);margin:15px}.overlay button{position:relative;z-index:25;margin-top:24px}
.confetti{position:absolute;inset:0;overflow:hidden;pointer-events:none}.confetti i{position:absolute;top:-30px;width:15px;height:9px;animation:fall 3s linear infinite}@keyframes fall{to{transform:translateY(1150px) rotate(720deg)}}

.pod:not(.m) .ag.r3{height:88%}.pod.m .ph,.pod.m .r1 .ph{width:70px;height:70px}.rw{height:74px}.weekly-status{font-size:14px;color:var(--gold2)}
.st b{font-size:26px}.pod.m .st b{font-size:22px}.st span{font-size:9px;letter-spacing:.5px}
</style>
