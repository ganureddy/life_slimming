// Web Page entry: reuse the portal views and permissions without changing the URL.
import { createApp } from 'vue';
import { createRouter, createMemoryHistory } from 'vue-router';
import App from './src/App.vue';
import { routes, routeLoading } from './src/router';
import { loadSession, session } from './src/lib/session';
import './src/style.css';
import '../life_slimming/public/css/portal_theme.css';

const host = document.getElementById('life-standalone-root');
const moduleId = host?.dataset.module;
const router = createRouter({
  history: createMemoryHistory('/life_portal/'),
  routes,
  scrollBehavior: () => ({ top: 0 }),
});
router.beforeEach(async (to, from) => {
  routeLoading.value = true;
  if (!to.meta.public && !from.name) {
    await loadSession();
    if (!session.user) return { name: 'login', replace: true };
  }
});
router.afterEach(to => {
  routeLoading.value = false;
  document.title = `${to.meta.title} · LIFE Portal`;
});
router.onError(() => { routeLoading.value = false; });

async function start() {
  if (!host || !moduleId || !router.hasRoute(moduleId)) throw new Error('Unknown portal module.');
  await router.replace({ name: moduleId, query: Object.fromEntries(new URLSearchParams(location.search)) });
  createApp(App).use(router).mount(host);
}
start().catch(error => {
  if (host) {
    host.setAttribute('role', 'alert');
    host.textContent = `Could not open portal page: ${error.message || error}`;
  }
});
