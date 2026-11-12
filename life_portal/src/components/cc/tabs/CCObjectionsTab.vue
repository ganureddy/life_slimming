<script setup>
import { inject, toRefs } from 'vue';
import { ccDashboardKey } from '../../../lib/cc-dashboard-context';

const { objections, copyText } = toRefs(inject(ccDashboardKey));
</script>

<template>
<section id="objections-area" class="card"><header class="card-hdr">🛡️ Objection Handling Guide</header><div class="card-body"><details v-for="item in objections" :key="item.obj" class="acc-item"><summary class="acc-hdr">🛡️ “{{item.obj}}”<span class="acc-icon">▼</span></summary><div class="acc-body"><div class="script-card"><div class="sc-title">✅ Recommended Response</div><div class="sc-text" style="white-space:pre-line">{{item.response}}</div><div class="agent-tip">💡 <strong>Key Strategy:</strong> {{item.tip}}</div><button class="copy-btn" @click="copyText(item.response)">📋 Copy</button></div></div></details></div></section>
</template>
