<script setup>
import { useRouter } from 'vue-router';
import StockDashboardHeader from '../components/stock/StockDashboardHeader.vue'; import StockDashboardNavigation from '../components/stock/StockDashboardNavigation.vue'; import StockSuppliersTab from '../components/stock/tabs/StockSuppliersTab.vue'; import '../styles/stock-native.css';
const now=new Date(), router=useRouter(); const tabs=[['dashboard','Dashboard'],['requests','Requests & Approvals'],['reports','Reports'],['procurement','Purchase Orders / Receipts'],['suppliers','Suppliers']]; const select=view=>router.push(`/stock-native/${view}`);
</script>
<template><main class="stock-native"><StockDashboardHeader :current-time="now" branch-name="Stock" employee-name="LIFE Portal" /><StockDashboardNavigation :items="tabs" active-view="suppliers" @select="select" /><StockSuppliersTab /></main></template>
