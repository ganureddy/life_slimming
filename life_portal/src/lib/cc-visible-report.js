import { watch } from 'vue';

// KeepAlive does not stop watchers. Only the visible report may initiate reads.
// Remember the completed argument key so simply returning to a tab is free.
export function watchVisibleReport(args, visible, load, ready) {
  let loadedKey = null, pendingKey = null;
  return watch(() => [visible(), ...args()], async ([shown, ...values]) => {
    if (!shown) return;
    const key = JSON.stringify(values);
    if (pendingKey === key || (loadedKey === key && ready())) return;
    pendingKey = key;
    try {
      await load(values);
      if (JSON.stringify(args()) === key && ready()) loadedKey = key;
    } finally {
      if (pendingKey === key) pendingKey = null;
    }
  }, { immediate: true });
}
