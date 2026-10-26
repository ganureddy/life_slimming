<script setup>defineProps({color:String,accent:String});</script>
<template><svg class="lady" viewBox="0 -10 56 62" width="46" height="51" aria-hidden="true">
    <g class="leg-b"><path d="M25 29 L28 38 L25 47 L29 48" fill="none" stroke="#8E5E3B" stroke-width="3.3" stroke-linecap="round" stroke-linejoin="round"/></g>
    <g class="arm-b"><path d="M27 16 L21 22 L25 26" fill="none" stroke="#8E5E3B" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/></g>
    <line x1="41" y1="-9" x2="41" y2="16" stroke="#F3EBD2" stroke-width="1.6" stroke-linecap="round"/>
    <path class="flag" d="M41 -9 C35 -11 31 -5 24 -8 L24 1 C31 3 35 -3 41 -1 Z" fill="#22C55E" stroke="#0B6B3F" stroke-width=".7"/>
    <path class="pony" d="M27 4 Q19 2 15 9 Q21 7 26 8 Z" fill="#24160D"/>
    <path d="M28.5 13 L25 29" :stroke="color" stroke-width="7.5" stroke-linecap="round"/>
    <path d="M20.5 27 L29.5 27 L32 34 L18.5 34 Z" :fill="accent" :stroke="color" stroke-width=".8"/>
    <g class="leg-f"><path d="M25 29 L28 38 L25 47 L29 48" fill="none" stroke="#C98B5E" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"/></g>
    <path d="M28.5 16 L35 13 L41 11" fill="none" stroke="#C98B5E" stroke-width="2.9" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="30" cy="7" r="5" fill="#C98B5E"/><path d="M25 7 A5 5 0 0 1 35 6 Q30 3.5 25 7 Z" fill="#24160D"/></svg></template>
