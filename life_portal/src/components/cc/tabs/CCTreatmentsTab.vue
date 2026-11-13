<script setup>
import { inject, toRefs } from 'vue';
import { ccDashboardKey } from '../../../lib/cc-dashboard-context';

const { treatments } = toRefs(inject(ccDashboardKey));
</script>

<template>
<section id="treatments-area" class="card"><header class="card-hdr">💉 Treatment Knowledge Base</header><div class="card-body"><details v-for="item in treatments" :key="item.name" class="acc-item"><summary class="acc-hdr">{{item.icon}} {{item.name}}<span class="pill p-blue">{{item.cat}}</span><span class="acc-icon">▼</span></summary><div class="acc-body"><div class="form-grid"><div><div class="form-section-title">Purpose</div><p>{{item.purpose}}</p></div><div><div class="form-section-title">Suitable For</div><p>{{item.suitableFor}}</p></div></div><div class="form-section-title">Benefits</div><p v-for="benefit in item.benefits" :key="benefit">{{benefit}}</p><div class="form-grid"><p><b>Sessions:</b> {{item.sessions}}</p><p><b>Recovery:</b> {{item.recovery}}</p><p><b>Pain Level:</b> {{item.pain}}</p><p><b>Results:</b> {{item.results}}</p></div><p><b>Cannot take:</b> <span style="color:#c00000">{{item.cannotTake}}</span></p><h4>FAQs:</h4><div v-for="faq in item.faq" :key="faq.q" class="script-card"><b>{{faq.q}}</b><p>{{faq.a}}</p></div></div></details></div></section>
</template>
