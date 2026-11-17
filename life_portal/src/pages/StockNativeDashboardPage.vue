<script setup>
import { useRouter } from 'vue-router';
import StockDashboardHeader from '../components/stock/StockDashboardHeader.vue';
import StockDashboardNavigation from '../components/stock/StockDashboardNavigation.vue';
import StockDashboardOverviewTab from '../components/stock/tabs/StockDashboardOverviewTab.vue';
import '../styles/stock-native.css';

const now = new Date();
const router = useRouter();
const tabs = [['dashboard', 'Dashboard'], ['requests', 'Requests & Approvals'], ['reports', 'Reports'], ['procurement', 'Purchase Orders / Receipts'], ['suppliers', 'Suppliers']];
const select = view => router.push(`/stock-native/${view}`);
</script>

<template>
  <main class="stock-native">
    <StockDashboardHeader :current-time="now" branch-name="Stock" employee-name="LIFE Portal" />
    <StockDashboardNavigation :items="tabs" active-view="dashboard" @select="select" />
    <StockDashboardOverviewTab />
  </main>
</template>
