<script setup>
import { inject, toRefs } from 'vue';
import { ccDashboardKey } from '../../../lib/cc-dashboard-context';

const { faqSearch, filteredFaqs, copyText } = toRefs(inject(ccDashboardKey));
</script>

<template>
<section id="faq-area" class="card"><header class="card-hdr">❓ FAQ &amp; Knowledge Base<input id="faq-search" v-model="faqSearch" placeholder="Search FAQs..." class="ff-input" style="width:200px;height:28px"></header><div class="card-body"><div id="faq-list"><section v-for="category in [...new Set(filteredFaqs.map(item=>item.cat))]" :key="category" style="margin-bottom:14px"><div class="form-section-title">{{category}}</div><details v-for="item in filteredFaqs.filter(item=>item.cat===category)" :key="item.q" class="acc-item"><summary class="acc-hdr">{{item.q}}<span class="acc-icon">▼</span></summary><div class="acc-body"><p>{{item.a}}</p><button class="copy-btn" @click="copyText(item.a)">📋 Copy Answer</button></div></details></section></div></div></section>
</template>
