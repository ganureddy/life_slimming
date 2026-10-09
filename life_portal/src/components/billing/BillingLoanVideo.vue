<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { uploadBillingFile } from '../../api/billing';
import { indiaStamp } from '../../lib/cc';
const props = defineProps({ client: String, branch: String });
const emit = defineEmits(['verified','busy-change']);
const preview = ref(null), recording = ref(false), busy = ref(false), heard = ref(''), error = ref(''), uploaded = ref('');
const selectedFile = ref(null), reviewUrl = ref(''), confirmed = ref(false);
watch(()=>recording.value || busy.value,value=>emit('busy-change',value));
const statement = computed(() => `Hi, my name is ${props.client}. I am voluntarily taking a loan from ${props.branch} for my treatment. I agree to the terms and conditions. Date: ${indiaStamp().slice(0,10)}`);
let stream, recorder, speech, timer, chunks = [], alive = true;
function cleanup() { clearTimeout(timer); if (speech) { speech.onend = null; speech.stop(); } stream?.getTracks().forEach(t => t.stop()); }
async function start() {
  if(recording.value || busy.value)return;
  clearReview();
  error.value = ''; uploaded.value = ''; heard.value = ''; emit('verified', null);
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) { error.value = 'Speech recognition is required for loan consent. Use a supported browser.'; return; }
  busy.value=true;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
    if (!alive) { cleanup(); return; }
    preview.value.srcObject = stream;
    speech = new Recognition(); speech.lang = 'en-IN'; speech.continuous = true;
    speech.onresult = event => { for (let i = event.resultIndex; i < event.results.length; i++) if (event.results[i].isFinal) heard.value += ' ' + event.results[i][0].transcript.toLowerCase(); };
    speech.onend = () => { if (recording.value) { try { speech.start(); } catch {} } };
    speech.start(); chunks = [];
    recorder = new MediaRecorder(stream, { videoBitsPerSecond: 200000, audioBitsPerSecond: 32000 });
    recorder.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
    recorder.onstop = save; recorder.start(500); recording.value = true;
    timer = setTimeout(stop, 120000);
  } catch (e) { cleanup(); error.value = e.message; } finally { busy.value=false; }
}
function clearReview() {
  if (reviewUrl.value) URL.revokeObjectURL(reviewUrl.value);
  reviewUrl.value = ''; selectedFile.value = null; confirmed.value = false;
}
function chooseVideo(event) {
  clearReview(); error.value = ''; uploaded.value = ''; emit('verified', null);
  const file = event.target.files?.[0]; event.target.value = '';
  if (!file) return;
  if (file.size>10*1024*1024) { error.value='Choose a video no larger than 10 MB.'; return; }
  if (!file.type.startsWith('video/')) { error.value = 'Choose a video file.'; return; }
  selectedFile.value = file; reviewUrl.value = URL.createObjectURL(file);
}
async function uploadReviewed() {
  if (busy.value || !selectedFile.value || !confirmed.value) return;
  busy.value = true; error.value = '';
  try {
    const url = await uploadBillingFile(selectedFile.value, 'Payment Entry');
    if (alive) { uploaded.value = url; emit('verified', { verified: true, url }); clearReview(); }
  } catch (e) { error.value = e.message; } finally { busy.value = false; }
}
function stop() { recording.value = false; clearTimeout(timer); if (recorder?.state !== 'inactive') recorder?.stop(); }
async function save() {
  cleanup(); if (!alive) return;
  const required = [...new Set([...props.client.toLowerCase().split(/\s+/).filter(w => w.length > 2), 'loan', props.branch.toLowerCase().split(/\s+/).find(w => w.length > 2) || 'life'])];
  if (required.filter(w => heard.value.includes(w)).length / required.length < .6) { error.value = 'Speech verification failed. Read the statement clearly and retry.'; return; }
  busy.value = true;
  try {
    const url = await uploadBillingFile(new File(chunks, 'loan-consent.webm', { type: recorder.mimeType }), 'Payment Entry');
    if (alive) { uploaded.value = url; emit('verified', { verified: true, url }); }
  } catch (e) { error.value = e.message; } finally { busy.value = false; }
}
onBeforeUnmount(() => { alive = false; clearReview(); if (recorder) recorder.onstop = null; stop(); cleanup(); });
</script>
<template>
  <div class="billing-panel billing-loan-video">
    <h3>Loan declaration video</h3><p>{{ statement }}</p>
    <video v-show="recording" ref="preview" autoplay muted playsinline aria-label="Live declaration recording"></video>
    <p v-if="heard">{{ heard }}</p>
    <div class="billing-fields"><button type="button" :disabled="recording || busy" @click="start">Record declaration</button><button v-if="recording" type="button" @click="stop">Stop and verify</button></div>
    <label>Or upload an existing declaration (up to 10 MB)<input type="file" accept="video/*" :disabled="recording || busy" @change="chooseVideo"></label>
    <div v-if="reviewUrl" class="billing-video-review">
      <h4>Review declaration</h4><p>{{ selectedFile.name }}</p>
      <video :src="reviewUrl" controls playsinline aria-label="Review uploaded declaration"></video>
      <label class="billing-checkbox"><input v-model="confirmed" type="checkbox" :disabled="busy">I watched and verified that the client is visible and clearly gives the loan declaration.</label>
      <div class="billing-fields"><button type="button" class="billing-primary" :disabled="!confirmed || busy" @click="uploadReviewed">Verify and upload</button><button type="button" :disabled="busy" @click="clearReview">Cancel upload</button></div>
    </div>
    <p v-if="busy" role="status">Uploading declaration…</p><p v-if="error" role="alert">{{ error }}</p><p v-if="uploaded" role="status">Declaration verified and uploaded.</p>
  </div>
</template>
