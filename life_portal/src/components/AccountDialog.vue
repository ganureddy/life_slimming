<script setup>
import { ref } from "vue";
import { session, initials, roleLabel, loginUrl } from "../lib/session";
import { call } from "../lib/api";
const dialog = ref(null);
const busy = ref(false);
const error = ref("");
defineExpose({
  open() {
    error.value = "";
    dialog.value.showModal();
  },
});
async function logout() {
  busy.value = true;
  error.value = "";
  try {
    await call("logout", {}, { csrfToken: session.csrf_token });
    window.location.assign(loginUrl());
  } catch (err) {
    error.value = err.message;
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <dialog
    ref="dialog"
    class="account-dialog"
    aria-labelledby="account-title"
    @click="
      (event) => {
        if (event.target === dialog && !busy) dialog.close();
      }
    "
    @cancel="
      (event) => {
        if (busy) event.preventDefault();
      }
    "
  >
    <button
      class="dialog-close"
      aria-label="Close"
      :disabled="busy"
      @click="dialog.close()"
    >
      ×
    </button>
    <h2 id="account-title">LIFE ERP</h2>
    <p class="muted">Enterprise Portal</p>
    <div class="account-details">
      <span class="avatar">{{ initials }}</span>
      <div>
        <strong>{{ session.full_name }}</strong>
        <p>{{ roleLabel }}</p>
        <small>{{ session.user }}</small>
      </div>
    </div>
    <h3>Sign out of LIFE ERP?</h3>
    <p class="muted">You will be signed out of your current ERP session.</p>
    <p v-if="error" role="alert">{{ error }}</p>
    <div class="actions">
      <button :disabled="busy" @click="dialog.close()">Cancel</button
      ><button class="danger" :disabled="busy" @click="logout">
        {{ busy ? "Signing out…" : "Logout" }}
      </button>
    </div>
  </dialog>
</template>
