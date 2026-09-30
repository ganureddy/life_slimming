import { computed, reactive } from "vue";

// Each page owns a token, so unmounting an old page cannot clear a new load.
const pending = reactive(new Map());
export const workspaceLoading = computed(() => pending.size > 0);
export const loadingDetail = computed(() => [...pending.values()].at(-1) || {});
export function beginLoading(label = "Loading workspace", retry = null) {
  const token = Symbol(label);
  pending.set(token, { label, retry });
  return () => pending.delete(token);
}
