<template>
  <section class="conversion-panel">
    <div class="conversion-links">
      <a href="/life_portal/p2p" target="_blank" rel="noopener">P2P CONVERSIONS <span>↗</span></a>
      <a href="/life_portal/c2c" target="_blank" rel="noopener">C2C CONVERSIONS <span>↗</span></a>
      <a href="/life_portal/b2b" target="_blank" rel="noopener">B2B TRANSFER <span>↗</span></a>
    </div>
  </section>
</template>

<style scoped>
.conversion-panel{padding:26px 30px 32px;background:rgba(255,255,255,.92);border:1px solid #dce9de;border-radius:16px;box-shadow:0 6px 24px #0f3d1e14}
.conversion-links{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:24px}
a{display:flex;align-items:center;justify-content:space-between;min-height:68px;padding:18px 20px;border:1px solid #dce9de;border-radius:12px;background:white;color:#173f25;font-size:14px;font-weight:700;text-decoration:none}
a:hover{background:#f3faf4;border-color:#a5d6a7}
@media(max-width:900px){.conversion-links{grid-template-columns:1fr;gap:12px}}
</style>
