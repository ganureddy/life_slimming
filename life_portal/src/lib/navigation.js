/** Return to the actual portal page the user came from, with a safe fallback for direct links. */
export function goToPreviousPage(router, fallback) {
  if (window.history.state?.back) {
    router.back();
    return;
  }
  router.push(fallback);
}
