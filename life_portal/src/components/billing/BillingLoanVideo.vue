<script setup>
import { computed, onBeforeUnmount, ref } from 'vue';
import { uploadBillingFile } from '../../api/billing';
import { indiaStamp } from '../../lib/cc';
const props = defineProps({ client: String, branch: String });
const emit = defineEmits(['verified']);
const preview = ref(null), recording = ref(false), busy = ref(false), heard = ref(''), error = ref(''), uploaded = ref('');
const statement = computed(() => `Hi, my name is ${props.client}. I am voluntarily taking a loan from ${props.branch} for my treatment. I agree to the terms and conditions. Date: ${indiaStamp().slice(0,10)}`);
let stream, recorder, speech, timer, chunks = [], alive = true;
function cleanup() { clearTimeout(timer); if (speech) { speech.onend = null; speech.stop(); } stream?.getTracks().forEach(t => t.stop()); }
async function start() {
  error.value = ''; uploaded.value = ''; heard.value = ''; emit('verified', null);
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) { error.value = 'Speech recognition is required for loan consent. Use a supported browser.'; return; }
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
  } catch (e) { cleanup(); error.value = e.message; }
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
onBeforeUnmount(() => { alive = false; if (recorder) recorder.onstop = null; stop(); cleanup(); });
</script>
<template><div class="billing-panel"><h3>Loan declaration video</h3><p>{{ statement }}</p><video ref="preview" autoplay muted playsinline style="width:100%;max-height:220px"></video><p>{{ heard }}</p><button type="button" :disabled="recording || busy" @click="start">Record declaration</button><button type="button" :disabled="!recording" @click="stop">Stop and verify</button><p v-if="error" role="alert">{{ error }}</p><p v-if="uploaded" role="status">Declaration verified and uploaded.</p></div></template>
