import { computed, reactive } from "vue";

// Each page owns a token, so unmounting an old page cannot clear a new load.
const pending = reactive(new Map());
export const workspaceLoading = computed(() => pending.size > 0);
export const loadingDetail = computed(() => [...pending.values()].at(-1) || {});
export function beginLoading(label = "Loading workspace", retry = null, maxDuration = 60000) {
  const token = Symbol(label);
  pending.set(token, { label, retry });
  // A request that never settles must not leave the full-page loader covering
  // every route forever. Owners still release their token immediately in
  // finally/on unmount; this timer is a final recovery path.
  const timeout = setTimeout(() => pending.delete(token), maxDuration);
  let finished = false;
  return () => {
    if (finished) return;
    finished = true;
    clearTimeout(timeout);
    pending.delete(token);
  };
}
