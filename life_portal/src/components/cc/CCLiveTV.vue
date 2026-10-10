<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { request } from '../../api/http';
import { apiUrl } from '../../api/config';
import { leaderboard, rank, changes, kinds } from '../../lib/cc-live-tv';
const root = ref(null), data = ref(null), error = ref(''), clock = ref(new Date()), sound = ref(false), soundError = ref('');
const feed = ref([]), active = ref(null), scale = ref(1), lastUpdated = ref(null);
const agents = computed(() => data.value ? leaderboard(data.value) : []);
const totals = computed(() => agents.value.reduce((sum, agent) => { for (const key in sum) sum[key] += agent.today[key]; return sum; }, {leads:0, booked:0, walkins:0, visitedBooked:0}));
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
    data.value = next;
    const winner = rank(agents.value, 'today')[0];
    feed.value = [...events.slice().reverse(), ...feed.value].slice(0,7);
    queue.push(...events);
    if (events.some(event => event.type === 'walkin') && oldWinner && winner && oldWinner.id !== winner.id) queue.push({id:`champ:${next.timestamp}`,type:'champ',agent:winner.name,client:'#1 Agent of the Day',time:next.timestamp});
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
  gain.gain.exponentialRampToValueAtTime(0.16, start + 0.025);
  gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);
  oscillator.connect(gain); gain.connect(audio.destination);
  oscillator.start(start); oscillator.stop(start + duration + 0.05);
  oscillator.onended = () => { oscillator.disconnect(); gain.disconnect(); };
}
function play(type) {
  const notes = {lead:[784,784],booked:[523,659,784],walkin:[523,659,784,1047],champ:[523,659,784,1047,784,1047,1319]}[type];
  notes.forEach((frequency,index) => tone(frequency, index * (type === 'lead' ? 1.3 : 0.2), type === 'lead' ? 2 : 1));
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
  alertTimer = setTimeout(dismiss, active.value.type === 'champ' ? 8000 : 6000);
}
function dismiss() { clearTimeout(alertTimer); active.value = null; alertTimer = setTimeout(nextAlert,400); }
async function fullscreen() {
  try { if (document.fullscreenElement) await document.exitFullscreen(); else await root.value.requestFullscreen(); }
  catch { soundError.value = 'Fullscreen is unavailable. Use your browser fullscreen control.'; }
}
function keydown(event) { if (event.key.toLowerCase() === 'f' && !event.ctrlKey && !event.metaKey) fullscreen(); }
onMounted(() => {
  observer = new ResizeObserver(([entry]) => { scale.value = Math.min(entry.contentRect.width / 1920, entry.contentRect.height / 1080); });
  observer.observe(root.value);
  document.addEventListener('keydown',keydown);
  clockTimer = setInterval(() => clock.value = new Date(),1000);
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
        <div class="chips"><div v-for="(label,key) in {leads:'LEADS TODAY',booked:'APPOINTMENT BOOKED',walkins:'VISITED',visitedBooked:'VISITED BOOKED'}" :key="key" class="chip"><b>{{ data ? totals[key] : '—' }}</b><span>{{ label }}</span></div></div>
        <div class="clock">{{ timeText }}<small>{{ dateText }}</small></div>
      </header>
      <main><section><template v-for="period in ['today','month']" :key="period">
        <div class="sec" :class="{'month-heading':period==='month'}">{{ period === 'today' ? '⭐ TODAY’S TOP 3 · VISITED' : '🏆 THIS MONTH TOP 3' }}</div>
        <div class="pod" :class="{m:period==='month'}">
          <template v-for="slot in podium(period)" :key="slot.rank"><article v-if="slot.agent" class="ag" :class="`r${slot.rank}`">
            <div v-if="slot.rank===1" class="crown">👑</div><div class="rank">#{{ slot.rank }}</div>
            <div class="ph"><img v-if="agentImage(slot.agent.id)" :key="agentImage(slot.agent.id)" :src="agentImage(slot.agent.id)" :alt="slot.agent.name" @error="imageFailed"><span v-else>{{ initials(slot.agent.name) }}</span></div><div class="nm">{{ slot.agent.name }}</div><div class="br">📍 {{ slot.agent.branch || 'Branch not assigned' }}</div>
            <div class="st"><div v-for="(label,key) in {walkins:'VISITED',visitedBooked:'VISITED BOOKED',booked:'APPOINTMENT BOOKED',leads:'LEADS'}" :key="key"><b>{{ slot.agent[period][key] }}</b><span>{{ label }}</span></div></div>
          </article><article v-else class="ag empty">{{ data ? 'No ranked activity yet' : 'Loading live data…' }}</article></template>
        </div>
      </template></section>
      <section class="right"><div class="sec">🔔 LATEST LEAD</div><div class="latest"><div class="bell">🔔</div><div><small>LATEST LEAD RECEIVED</small><h3>{{ latest?.lead_name || 'Waiting for leads…' }}</h3><p v-if="latest">{{ data.agents[latest.lead_owner] || 'Unassigned' }} · {{ latest.source }} · {{ latest.branch || latest.lead_assign_to_branch }}</p></div></div>
        <div class="sec">LIVE ACTIVITY</div><div class="feed"><div v-for="event in feed" :key="event.id" class="ev" :style="{'--k':kinds[event.type].color}"><div class="ic">{{ kinds[event.type].icon }}</div><div><b>{{ kinds[event.type].title }} · {{ event.client }}</b><span>{{ event.agent }} · {{ event.branch }}</span></div><em>{{ event.time.slice(11,16) }}</em></div><p v-if="!feed.length" class="empty">New activity will appear here while this screen is open.</p></div>
      </section></main>
      <div v-if="active" class="overlay" :style="{'--oc':kinds[active.type].color}"><div><div class="ico">{{ kinds[active.type].icon }}</div><div class="big">{{ kinds[active.type].title }}</div><h2>{{ active.client }}</h2><p>{{ active.agent }} {{ active.branch ? ' · '+active.branch : '' }}</p><p v-if="active.type==='lead'">{{ [active.source,active.treatment].filter(Boolean).join(' · ') }} · CALL NOW!</p><button @click="dismiss">Dismiss</button></div>
        <div v-if="['walkin','champ'].includes(active.type)" class="confetti" aria-hidden="true"><i v-for="n in 65" :key="n" :style="{left:`${(n*37)%100}%`,animationDelay:`${(n%11)*.13}s`,background:['#f5c542','#2ecc71','#4da3ff','#ff6b9d'][n%4]}" /></div>
      </div>
      <footer><span role="status">{{ error || (data ? (data.restricted_to_owner ? 'Your assigned leads' : 'All CC leads') + ' · Refreshes every 5 seconds · Visits by appointment date' : 'Connecting to live data…') }}<template v-if="lastUpdated"> · Updated {{ lastUpdated.toLocaleTimeString('en-IN', {timeZone:zone}) }}</template></span><span role="status">{{ soundError }}</span><RouterLink :to="{name:'leads-native'}">Dashboard</RouterLink><button @click="fullscreen">⛶ Fullscreen</button><button :aria-pressed="sound" @click="toggleSound">{{ sound ? '🔊 Sound on' : '🔇 Enable sound' }}</button></footer>
    </div>
  </div>
</template>

<style scoped>

.cc-tv{--bg:#06150e;--g1:#0f3d2a;--g2:#1c6b46;--gold:#f5c542;--gold2:#ffdf8a;--ink:#f4f1e6;--mut:#9db8a8;--red:#ff4d4d;--blue:#4da3ff;--card:rgba(255,255,255,.06)}
*{box-sizing:border-box;margin:0}
.cc-tv{height:100%;overflow:hidden;background:var(--bg);font-family:"Segoe UI",Inter,system-ui,sans-serif;color:var(--ink)}
.tv-stage{position:absolute;left:0;top:0;width:1920px;height:1080px;transform-origin:0 0;background:radial-gradient(1200px 700px at 20% 0,#14573a 0,transparent 60%),radial-gradient(900px 600px at 100% 100%,#0d3b5a55 0,transparent 60%),var(--bg)}
header{height:96px;display:flex;align-items:center;gap:28px;padding:0 44px;border-bottom:2px solid #ffffff14}
.logo{width:60px;height:60px;border-radius:16px;background:linear-gradient(135deg,var(--gold),#c58f10);color:#2b1d00;font:800 38px Georgia,serif;display:grid;place-items:center}
h1{font:700 34px Georgia,serif;letter-spacing:5px}h1 small{display:block;font:600 15px "Segoe UI";letter-spacing:6px;color:var(--mut)}
.live{display:flex;align-items:center;gap:10px;font-weight:800;letter-spacing:3px;color:var(--red)}.live i{width:14px;height:14px;border-radius:50%;background:var(--red);animation:blink 1.2s infinite}
.chips{margin-left:auto;display:flex;gap:12px}
.chip{background:var(--card);border:1px solid #ffffff1a;border-radius:16px;padding:8px 14px;text-align:center}.chip b{display:block;font-size:34px;color:var(--gold)}.chip span{font-size:13px;letter-spacing:3px;color:var(--mut)}
.clock{font:300 48px "Segoe UI";text-align:right;min-width:200px}.clock small{display:block;font-size:16px;color:var(--mut);letter-spacing:2px}
main{display:grid;grid-template-columns:1180px 1fr;gap:28px;padding:24px 44px;height:984px}
.sec{font:800 22px "Segoe UI";letter-spacing:6px;color:var(--gold);margin-bottom:14px;display:flex;align-items:center;gap:12px}.sec:after{content:"";flex:1;height:2px;background:linear-gradient(90deg,#f5c54266,transparent)}
.pod{display:grid;grid-template-columns:1fr 1.18fr 1fr;gap:20px;align-items:end;height:470px}
.pod.m{height:300px;grid-template-columns:1fr 1fr 1fr;align-items:stretch}
.ag{position:relative;background:linear-gradient(180deg,#ffffff10,#ffffff05);border:1px solid #ffffff1f;border-radius:26px;padding:20px 12px 16px;text-align:center;display:flex;flex-direction:column;align-items:center;justify-content:flex-end}
.ag.r1{height:100%;border-color:var(--gold);box-shadow:0 0 50px #f5c54255,inset 0 0 40px #f5c54218;background:linear-gradient(180deg,#f5c54222,#ffffff06)}
.ag.r2{height:86%}.ag.r3{height:78%}.pod.m .ag{height:100%!important}
.ph{width:150px;height:150px;border-radius:50%;border:5px solid var(--c,#9db8a8);background:#123 center/cover;display:grid;place-items:center;font:800 54px Georgia,serif;color:#fff;box-shadow:0 8px 30px #0008}
.ph{overflow:hidden;flex-shrink:0}.ph img{width:100%;height:100%;object-fit:cover;display:block;min-height:0}
.r1{--c:var(--gold)}.r1 .ph{width:200px;height:200px;font-size:72px}.r2{--c:#d6dde3}.r3{--c:#d9945a}.pod.m .ph{width:96px;height:96px;font-size:36px}.pod.m .r1 .ph{width:96px;height:96px}
.crown{position:absolute;top:-34px;font-size:60px;animation:float 2s ease-in-out infinite;filter:drop-shadow(0 4px 10px #f5c54299)}
.rank{position:absolute;top:12px;left:16px;font:900 46px Georgia,serif;color:var(--c)}.pod.m .rank{font-size:30px}
.nm{font:700 30px "Segoe UI";margin-top:12px}.r1 .nm{font-size:38px}.pod.m .nm{font-size:23px;margin-top:6px}
.br{color:var(--mut);font-size:17px;letter-spacing:1px}
.st{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));width:100%;gap:6px;margin-top:10px}.st div{background:#0006;border-radius:12px;padding:6px 4px}.st b{font-size:34px;display:block;color:var(--gold2)}.st span{font-size:12px;letter-spacing:2px;color:var(--mut)}
.pod.m .st b{font-size:24px}.pod.m .st div{padding:4px}
.pop{animation:pop .9s}
.right{display:flex;flex-direction:column;gap:16px;min-height:0}
.latest{border-radius:26px;padding:22px 26px;background:linear-gradient(135deg,#7a5200,#c58f10);color:#fff;display:flex;gap:20px;align-items:center;min-height:170px;box-shadow:0 0 40px #f5c54244}
.latest .bell{font-size:78px;animation:ring 1.6s infinite;transform-origin:50% 10%}.latest small{letter-spacing:5px;font-weight:800;opacity:.85}.latest h3{font:800 40px "Segoe UI";line-height:1.1}.latest p{font-size:21px;opacity:.92}
.feed{flex:1;overflow:hidden;display:flex;flex-direction:column;gap:10px}
.ev{display:flex;gap:16px;align-items:center;padding:14px 18px;border-radius:18px;background:var(--card);border-left:8px solid var(--k);animation:slide .6s}
.ev .ic{font-size:36px}.ev b{font-size:24px;display:block}.ev span{color:var(--mut);font-size:17px}.ev em{margin-left:auto;font-style:normal;color:var(--mut);font-size:16px}
@keyframes blink{50%{opacity:.2}}@keyframes float{50%{transform:translateY(-10px)}}
@keyframes ring{0%,50%,100%{transform:rotate(0)}10%{transform:rotate(22deg)}20%{transform:rotate(-20deg)}30%{transform:rotate(16deg)}40%{transform:rotate(-12deg)}}
@keyframes pop{0%{transform:scale(.85)}50%{transform:scale(1.07)}100%{transform:scale(1)}}
@keyframes slide{from{transform:translateX(80px);opacity:0}}@keyframes fade{from{opacity:0}}@keyframes zoom{from{transform:scale(.3);opacity:0}}

.cc-tv{position:fixed;inset:0;z-index:1100;width:100vw;height:100dvh;background:#06150e}
.tv-stage{left:50%;top:50%;transform-origin:center}
main{height:924px}.month-heading{margin-top:26px}.clock small{text-transform:uppercase}.live.offline{color:#ffdf8a}.live.offline i{background:#ffdf8a}
.nm{max-width:100%;font-size:28px;line-height:1.1;overflow-wrap:anywhere}.r1 .nm{font-size:32px}.latest h3{overflow-wrap:anywhere}.empty{color:var(--mut);text-align:center;padding:24px}
footer{height:60px;padding:8px 24px;display:flex;gap:15px;align-items:center;font-size:16px}footer>span:first-child{margin-right:auto;max-width:1100px}button,footer a{border:1px solid #fff4;background:#ffffff18;color:white;border-radius:10px;padding:10px 16px;cursor:pointer;white-space:nowrap;font:inherit}
.overlay{position:absolute;inset:0;display:grid;place-items:center;text-align:center;z-index:20;background:radial-gradient(circle,color-mix(in srgb,var(--oc) 35%,#06150e),#020a06 75%)}
.overlay .big{font:900 110px/1.1 'Segoe UI',sans-serif;color:var(--oc);max-width:1800px}.overlay .ico{font-size:220px;animation:ring 1.6s infinite}.overlay h2{font-size:70px;max-width:1700px;overflow-wrap:anywhere}.overlay p{font-size:42px;color:var(--gold2);margin:15px}.overlay button{position:relative;z-index:25;margin-top:24px}
.confetti{position:absolute;inset:0;overflow:hidden;pointer-events:none}.confetti i{position:absolute;top:-30px;width:15px;height:9px;animation:fall 3s linear infinite}@keyframes fall{to{transform:translateY(1150px) rotate(720deg)}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important}.confetti{display:none}}
</style>

<style scoped>
.chip span,.st span{display:block}
.chip span{max-width:150px}
.st span{line-height:1.3;font-size:11px;letter-spacing:1px;overflow-wrap:anywhere}
</style>
