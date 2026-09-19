<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  authApi,
  portalDestination,
  passwordResetDestination,
} from "../api/auth";
const route = useRoute();
const router = useRouter();
const stage = ref("credentials");
const username = ref("");
const password = ref("");
const showPassword = ref(false);
const otp = ref("");
const otpField = ref(null);
const busy = ref(false);
const initializing = ref(true);
const ready = ref(false);
const error = ref("");
const notice = ref("");
const csrfToken = ref("");
const passwordEnabled = ref(true);
const tmpId = ref("");
const verification = ref({});
const deadline = ref(0);
const now = ref(Date.now());
const retryAt = ref(0);
const challengeSeconds = ref(300);
const logoAvailable = ref(true);
let clock;
let alive = true;
const remaining = computed(() =>
  Math.max(0, Math.ceil((deadline.value - now.value) / 1000)),
);
const countdown = computed(
  () =>
    Math.floor(remaining.value / 60) +
    ":" +
    String(remaining.value % 60).padStart(2, "0"),
);
const resendWait = computed(() =>
  Math.max(0, Math.ceil((retryAt.value - now.value) / 1000)),
);
const isApp = computed(() => verification.value.method === "OTP App");
const prompt = computed(
  () =>
    verification.value.prompt ||
    (isApp.value
      ? "Enter the current six-digit code from your authenticator app."
      : "Enter the six-digit verification code sent to your registered contact."),
);
const destination = computed(() =>
  portalDestination(route.query["redirect-to"]),
);
const standardLogin = computed(
  () => "/login?redirect-to=" + encodeURIComponent(destination.value),
);

function clearChallenge() {
  tmpId.value = "";
  otp.value = "";
  deadline.value = 0;
  verification.value = {};
}
function back() {
  if (busy.value) return;
  clearChallenge();
  password.value = "";
  stage.value = "credentials";
  error.value = "";
  notice.value = "";
}
async function finish() {
  password.value = "";
  clearChallenge();
  await router.replace(destination.value.replace(/^\/life_portal/, "") || "/");
}
async function initialize() {
  initializing.value = true;
  ready.value = false;
  error.value = "";
  try {
    const context = await authApi.context();
    if (!alive) return;
    csrfToken.value = context.csrf_token || "";
    passwordEnabled.value = context.password_login_enabled;
    challengeSeconds.value = context.challenge_seconds || 300;
    ready.value = true;
    if (context.authenticated) await finish();
  } catch (err) {
    if (alive) error.value = err.message;
  } finally {
    if (alive) initializing.value = false;
  }
}
async function handleLogin(body) {
  if (!alive) return;
  if (body.message === "Password Reset") {
    const target = passwordResetDestination(body.redirect_to);
    if (!target)
      throw new Error(
        "A password change is required. Continue through the standard sign-in page.",
      );
    password.value = "";
    clearChallenge();
    window.location.assign(target);
    return;
  }
  const challenge = body.tmp_id || body.message?.tmp_id;
  if (challenge) {
    tmpId.value = challenge;
    verification.value = body.verification || body.message?.verification || {};
    stage.value = "verification";
    otp.value = "";
    now.value = Date.now();
    deadline.value = now.value + challengeSeconds.value * 1000;
    retryAt.value = now.value + 30000;
    if (verification.value.token_delivery === false)
      error.value =
        "The verification code could not be delivered. Please try again or contact your administrator.";
    await nextTick();
    otpField.value?.focus();
    return;
  }
  if (body.message === "Logged In" || body.message === "No App") {
    await finish();
    return;
  }
  throw new Error("Sign-in was not completed. Please try again.");
}
async function submitCredentials() {
  if (
    busy.value ||
    initializing.value ||
    !ready.value ||
    !username.value.trim() ||
    !password.value
  )
    return;
  busy.value = true;
  error.value = "";
  notice.value = "";
  try {
    await handleLogin(
      await authApi.login(
        { usr: username.value.trim(), pwd: password.value },
        csrfToken.value,
      ),
    );
  } catch (err) {
    if (alive) error.value = err.message;
  } finally {
    if (alive) busy.value = false;
  }
}
async function verify() {
  if (
    busy.value ||
    !/^\d{6}$/.test(otp.value) ||
    !tmpId.value ||
    !remaining.value
  )
    return;
  busy.value = true;
  error.value = "";
  notice.value = "";
  try {
    await handleLogin(
      await authApi.login(
        { otp: otp.value, tmp_id: tmpId.value },
        csrfToken.value,
      ),
    );
  } catch (err) {
    if (alive) {
      error.value = err.message;
      if (err.code === "ExpiredLoginException") deadline.value = 0;
    }
  } finally {
    if (alive) busy.value = false;
  }
}
async function resend() {
  if (busy.value || resendWait.value || isApp.value) return;
  if (!password.value) {
    back();
    return;
  }
  await submitCredentials();
}
async function resetPassword() {
  if (busy.value || !ready.value || !username.value.trim()) return;
  busy.value = true;
  error.value = "";
  notice.value = "";
  try {
    await authApi.resetPassword(username.value.trim(), csrfToken.value);
    if (alive)
      notice.value =
        "If this account is eligible, password reset instructions have been sent to its registered email address.";
  } catch (err) {
    if (alive) error.value = err.message;
  } finally {
    if (alive) busy.value = false;
  }
}
onMounted(() => {
  initialize();
  clock = setInterval(() => {
    now.value = Date.now();
  }, 1000);
});
onUnmounted(() => {
  alive = false;
  clearInterval(clock);
  password.value = "";
  clearChallenge();
});
</script>

<template>
  <main class="login-page">
    <section class="login-story" aria-label="LIFE Portal">
      <a class="login-brand" href="/life_portal/" aria-label="LIFE Portal Home"
        ><span class="login-leaf" aria-hidden="true">✳</span
        ><span
          >LIFE<span class="login-brand-sub"
            >SLIMMING &amp; COSMETIC CLINIC</span
          ></span
        ></a
      >
      <div class="login-story-copy">
        <p class="login-kicker">ONE TEAM. ONE WORKSPACE.</p>
        <h1>
          A little more focus.<br />
          A lot more <em>life.</em>
        </h1>
        <p>
          Your people, your branches, your everyday work.<br />All connected in
          one place.
        </p>
        <div class="login-story-tags">
          <span>Client care</span><span>Branch operations</span
          ><span>Teamwork</span>
        </div>
      </div>
      <div class="login-story-footer">
        <span>LIFE ENTERPRISE PORTAL</span><span>Built around you ↗</span>
      </div>
      <div class="login-orbit orbit-one" aria-hidden="true"></div>
      <div class="login-orbit orbit-two" aria-hidden="true"></div>
    </section>
    <section class="login-form-side">
      <div class="login-topline">
        <span>Welcome to your workspace</span
        ><span class="login-secure">◈ Secure sign-in</span>
      </div>
      <div class="login-card">
        <img
          v-if="logoAvailable"
          :src="'/files/life-logo.png'"
          alt="LIFE Clinics"
          class="login-logo"
          @error="logoAvailable = false"
        />
        <div v-else class="login-wordmark">LIFE<span>ERP PORTAL</span></div>
        <div v-if="initializing" class="login-loading" role="status">
          Preparing your secure sign-in…
        </div>
        <template v-else>
          <template v-if="!passwordEnabled"
            ><h2>Sign in to LIFE</h2>
            <p>Password sign-in is disabled for this site.</p>
            <a :href="standardLogin" class="login-submit"
              >Continue to sign in →</a
            ></template
          >
          <form
            v-else-if="stage === 'credentials'"
            @submit.prevent="submitCredentials"
          >
            <p class="login-step">LET’S GET STARTED</p>
            <h2>Good to see you.</h2>
            <p class="login-intro">Sign in with your LIFE ERP account.</p>
            <label for="login-username">Email or username</label
            ><input
              id="login-username"
              v-model="username"
              type="text"
              autocomplete="username"
              autocapitalize="none"
              spellcheck="false"
              placeholder="Your email or username"
              required
              :disabled="busy"
              maxlength="140"
            />
            <div class="login-label-row">
              <label for="login-password">Password</label
              ><button
                type="button"
                class="login-text-button"
                :disabled="busy"
                @click="
                  stage = 'reset';
                  password = '';
                  error = '';
                  notice = '';
                "
              >
                Forgot password?
              </button>
            </div>
            <div class="login-password-wrap">
              <input
                id="login-password"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                autocomplete="current-password"
                placeholder="Enter your password"
                required
                :disabled="busy"
                maxlength="512"
              /><button
                type="button"
                :aria-label="showPassword ? 'Hide password' : 'Show password'"
                :aria-pressed="showPassword"
                @click="showPassword = !showPassword"
              >
                {{ showPassword ? "Hide" : "Show" }}
              </button>
            </div>
            <button
              class="login-submit"
              :disabled="busy || initializing || !ready"
            >
              {{ busy ? "Signing in…" : "Sign in"
              }}<span aria-hidden="true">→</span>
            </button>
            <p class="login-help">
              If two-step verification is enabled for your account, we’ll ask
              for your verification code next.
            </p>
          </form>
          <form v-else-if="stage === 'verification'" @submit.prevent="verify">
            <button
              type="button"
              class="login-back"
              :disabled="busy"
              @click="back"
            >
              ← Back to sign in
            </button>
            <p class="login-step">ONE MORE STEP</p>
            <h2>Verify it’s you.</h2>
            <p class="login-intro">{{ prompt }}</p>
            <div
              v-if="verification.token_delivery === false"
              class="login-error"
              role="status"
            >
              Delivery unavailable. Contact your administrator if the problem
              continues.
            </div>
            <label for="login-otp">Verification code</label
            ><input
              id="login-otp"
              ref="otpField"
              v-model="otp"
              class="login-otp"
              type="text"
              inputmode="numeric"
              autocomplete="one-time-code"
              pattern="[0-9]{6}"
              maxlength="6"
              placeholder="000000"
              required
              :disabled="busy || !remaining"
              @input="otp = otp.replace(/\D/g, '').slice(0, 6)"
            />
            <p class="login-timer">
              {{
                remaining
                  ? "Session expires in " + countdown
                  : "This session has expired. Please start again."
              }}
            </p>
            <button
              class="login-submit"
              :disabled="busy || !remaining || otp.length !== 6"
            >
              {{ busy ? "Verifying…" : "Verify & sign in"
              }}<span aria-hidden="true">→</span>
            </button>
            <div class="login-resend">
              <span>{{
                isApp
                  ? "Use your authenticator app’s current code."
                  : "Didn’t receive a code?"
              }}</span
              ><button
                v-if="!isApp"
                type="button"
                class="login-text-button"
                :disabled="busy || resendWait > 0"
                @click="resend"
              >
                {{
                  resendWait ? "Resend in " + resendWait + "s" : "Resend code"
                }}
              </button>
            </div>
          </form>
          <form v-else @submit.prevent="resetPassword">
            <button
              type="button"
              class="login-back"
              :disabled="busy"
              @click="back"
            >
              ← Back to sign in
            </button>
            <p class="login-step">ACCOUNT RECOVERY</p>
            <h2>Forgot your password?</h2>
            <p class="login-intro">
              We’ll help you get back to your workspace.
            </p>
            <label for="reset-email">Account email</label
            ><input
              id="reset-email"
              v-model="username"
              type="email"
              autocomplete="username"
              required
              placeholder="Your registered email address"
              :disabled="busy"
            /><button class="login-submit" :disabled="busy">
              {{ busy ? "Sending…" : "Send reset instructions"
              }}<span aria-hidden="true">→</span>
            </button>
          </form>
        </template>
        <p v-if="error" role="alert" class="login-error">{{ error }}</p>
        <p v-if="notice" role="status" class="login-notice">{{ notice }}</p>
        <button
          v-if="error && !csrfToken && !initializing"
          class="login-text-button"
          @click="initialize"
        >
          Retry connection
        </button>
        <div class="login-divider"></div>
        <p class="login-support">
          Need help with your account?<br /><span
            >Contact your branch administrator.</span
          >
        </p>
      </div>
      <footer class="login-footer">
        <span>© {{ new Date().getFullYear() }} LIFE Clinics</span
        ><a :href="standardLogin">Standard sign-in ↗</a>
      </footer>
    </section>
  </main>
</template>

<style src="../styles/login.css"></style>
