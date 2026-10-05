import { createApp } from "vue";
import "./style.css";
import "../../life_slimming/public/css/portal_theme.css";
import App from "./App.vue";
import router from "./router";

// Legacy scripts may navigate their iframe to a portal route. Never mount a
// second workspace: promote that navigation to the top-level window.
if (window.top !== window.self) {
  window.top.location.replace(window.location.href);
} else {
  const app = createApp(App).use(router);
  router.isReady().then(() => app.mount("#app"));
}
