<script setup>
defineProps({ isHo: Boolean, branchName: String, employeeName: String, refreshing: Boolean, currentTime: { type: Date, default: () => new Date() }, canSwitchView: Boolean });
defineEmits(['refresh', 'select-view', 'settings']);
</script>

<template>
  <header class="life-stock-app-header stock-header" id="life-stock-app-header">
    <div class="life-stock-app-header__inner">
      <div class="life-stock-app-brand"><a class="life-stock-back-button" href="/life_portal/stock" title="Back to Stock App">←</a><div class="life-stock-app-brandcopy"><div class="life-stock-app-company">LIFE SLIMMING &amp; COSMETIC PVT. LTD.</div><h1>LIFE INVENTORY / STOCK MANAGEMENT SYSTEM</h1><p>Inventory · Material Requests · Approvals · Procurement</p></div></div>
      <div class="life-stock-app-header__meta">
        <button class="life-stock-header-chip" type="button" @click="$emit('settings')">⚙ <strong>Settings</strong></button>
        <a class="life-stock-header-chip life-stock-stock360-link" href="/life_portal/stores-360" target="_blank" rel="noopener noreferrer">360° <strong>Stock 360</strong> ↗</a>
        <div class="life-stock-header-chip life-stock-dashboard-view"><span>📍 DASHBOARD VIEW</span><button type="button" :aria-pressed="!isHo" @click="$emit('select-view', 'branch')">Branch</button><button type="button" :aria-pressed="isHo" @click="$emit('select-view', 'ho')">Stock Manager</button></div>
        <div class="life-stock-header-chip life-stock-header-chip--detail life-stock-location-card"><span>📍</span><span class="life-stock-header-chip__copy"><small>LOCATION</small><strong>{{ isHo ? 'Head Office' : (branchName || 'Resolving…') }}</strong><span v-if="canSwitchView" class="life-stock-view-switch"><button type="button" :aria-pressed="!isHo" @click="$emit('select-view', 'branch')">Branch</button><button type="button" :aria-pressed="isHo" @click="$emit('select-view', 'ho')">Stock Manager</button></span></span></div>
        <div class="life-stock-header-profile"><span class="life-stock-header-avatar">{{ (employeeName || 'U').charAt(0).toUpperCase() }}</span><span><small>{{ isHo ? 'STOCK MANAGER' : 'USER' }}</small><strong>{{ employeeName || 'Loading…' }}</strong></span></div>
        <div class="life-stock-header-clock"><strong>{{ currentTime.toLocaleDateString('en-IN',{weekday:'short',day:'2-digit',month:'short',year:'numeric'}) }}</strong><span>{{ currentTime.toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit',second:'2-digit'}) }}</span></div>
      </div>
    </div>
  </header>
</template>
