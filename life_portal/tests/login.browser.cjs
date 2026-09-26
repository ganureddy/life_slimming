// Run with Playwright available via NODE_PATH; all authentication responses are mocked.
const { chromium } = require("playwright");
const assert = require("node:assert/strict");
(async () => {
  const browser = await chromium.launch({
    executablePath: process.env.CHROME_PATH || "/usr/bin/google-chrome",
    headless: true,
    args: ["--no-sandbox"],
  });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
    reducedMotion: "reduce",
  });
  const page = await context.newPage();
  page.setDefaultTimeout(10000);
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  let loggedIn = false,
    mode = "SMS",
    loginHandler,
    posts = [];
  const config = () => ({
    authenticated: false,
    csrf_token: "mock-csrf",
    password_login_enabled: true,
    two_factor_method: mode,
    challenge_seconds: mode === "OTP App" ? 180 : 300,
  });
  let getContext = config;
  await page.route("**/api/method/life_slimming.api.auth.login_context", (r) =>
    r.fulfill({ json: { message: getContext() } }),
  );
  await page.route("**/api/method/life_slimming.api.portal.bootstrap", (r) =>
    r.fulfill(
      loggedIn
        ? {
            json: {
              message: {
                user: "Administrator",
                full_name: "Test Administrator",
                roles: ["System Manager"],
                portal_role: "",
                csrf_token: "signed-in-csrf",
                access_config: null,
              },
            },
          }
        : { status: 403, json: {} },
    ),
  );
  await page.route("**/api/method/login", async (r) => {
    const args = r.request().postDataJSON();
    posts.push(args);
    assert.equal(r.request().method(), "POST");
    assert.equal(r.request().headers()["x-frappe-csrf-token"], "mock-csrf");
    await r.fulfill(await loginHandler(args));
  });
  await page.route("**/files/**", (r) => r.fulfill({ status: 404, body: "" }));
  const base = process.env.PORTAL_URL || "http://127.0.0.1:5173";
  async function open(query = "") {
    loggedIn = false;
    await page.goto(base + "/life_portal/login" + query);
    await page.getByRole("heading", { name: "Good to see you." }).waitFor();
  }
  async function credentials() {
    await page.getByLabel("Email or username").fill("user@example.test");
    await page
      .getByLabel("Password", { exact: true })
      .fill("test-only-password");
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
  }
  const challenge = (id = "challenge-1", method = "SMS", delivery = true) => ({
    json: {
      tmp_id: id,
      verification: {
        method,
        token_delivery: delivery,
        prompt: "Enter the code sent to 91******123",
      },
    },
  });
  // Initial appearance and mobile layout.
  await open();
  await page.screenshot({
    path: "/tmp/life-login-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  assert(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  );
  await page.screenshot({ path: "/tmp/life-login-mobile.png", fullPage: true });
  await page.getByLabel("Password", { exact: true }).fill("test-only-password");
  await page
    .getByRole("button", { name: "Show password", exact: true })
    .click();
  assert.equal(
    await page.getByLabel("Password", { exact: true }).getAttribute("type"),
    "text",
  );
  await page
    .getByRole("button", { name: "Hide password", exact: true })
    .click();
  // Invalid credentials and direct login (including server-side 2FA bypass).
  loginHandler = () => ({
    status: 401,
    json: { exc_type: "AuthenticationError" },
  });
  await credentials();
  await page.getByRole("alert").waitFor();
  assert(page.url().includes("/login"));
  loginHandler = () => {
    loggedIn = true;
    return { json: { message: "Logged In" } };
  };
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("heading", { name: "Welcome, Test" }).waitFor();
  // Central API calls preserve non-message fields and send the current session CSRF.
  await page.route(
    "**/api/method/life_slimming.api.server_scripts.portal_is_system_manager.run",
    (r) => {
      assert.equal(r.request().method(), "POST");
      assert.equal(
        r.request().headers()["x-frappe-csrf-token"],
        "signed-in-csrf",
      );
      return r.fulfill({
        json: { message: { is_sys_mgr: 1 }, status: "success" },
      });
    },
  );
  const catalogueCheck = await page.evaluate(async () => {
    const { dataApi, endpoints } =
      await import("/life_portal/src/api/index.js");
    const response = await dataApi("portal_is_system_manager");
    let unknownRejected = false;
    try {
      await dataApi("unknown_method");
    } catch {
      unknownRejected = true;
    }
    return { count: Object.keys(endpoints).length, response, unknownRejected };
  });
  assert.equal(catalogueCheck.count, 141);
  assert.equal(catalogueCheck.response.status, "success");
  assert.equal(catalogueCheck.unknownRejected, true);
  // A 200 response without a successful login message must not grant access.
  await open();
  loginHandler = () => ({ json: { message: "Not a successful login" } });
  await credentials();
  await page.getByRole("alert").waitFor();
  assert(page.url().includes("/login"));
  // SMS challenge, invalid code, resend, and correct code preserve the target URL.
  await open("?redirect-to=%2Flife_portal%2Fbilling%3Finvoice%3DTEST");
  await page.clock.install();
  loginHandler = () => challenge();
  await credentials();
  await page.getByRole("heading", { name: "Verify it’s you." }).waitFor();
  assert.equal(await page.locator("nav").count(), 0);
  await page.getByLabel("Verification code", { exact: true }).fill("111111");
  loginHandler = () => ({
    status: 401,
    json: { exc_type: "AuthenticationError" },
  });
  await page
    .getByRole("button", { name: "Verify & sign in", exact: true })
    .click();
  await page.getByRole("alert").waitFor();
  assert.deepEqual(posts.at(-1), { otp: "111111", tmp_id: "challenge-1" });
  await page.clock.fastForward(31000);
  loginHandler = () => challenge("challenge-2");
  await page.getByRole("button", { name: "Resend code", exact: true }).click();
  await page.getByLabel("Verification code", { exact: true }).fill("222222");
  loginHandler = () => {
    loggedIn = true;
    return { json: { message: "Logged In" } };
  };
  await page
    .getByRole("button", { name: "Verify & sign in", exact: true })
    .click();
  await page
    .getByRole("heading", { name: "Billing & Invoices", level: 1 })
    .waitFor();
  assert.deepEqual(posts.at(-1), { otp: "222222", tmp_id: "challenge-2" });
  assert(page.url().endsWith("/life_portal/billing?invoice=TEST"));
  assert.equal(
    await page.evaluate(() =>
      Object.keys(localStorage).some((k) => /pwd|password|otp|tmp_id/i.test(k)),
    ),
    false,
  );
  // Expiry and authenticator-app mode: no SMS-only resend controls.
  mode = "OTP App";
  await open();
  loginHandler = () => challenge("app-challenge", "OTP App");
  await credentials();
  await page.getByRole("heading", { name: "Verify it’s you." }).waitFor();
  assert.equal(await page.getByRole("button", { name: /Resend/ }).count(), 0);
  await page.clock.fastForward(181000);
  assert(
    await page
      .getByRole("button", { name: "Verify & sign in", exact: true })
      .isDisabled(),
  );
  await page
    .getByRole("button", { name: "Back to sign in", exact: false })
    .click();
  assert.equal(
    await page.getByLabel("Password", { exact: true }).inputValue(),
    "",
  );
  // Delivery failures remain on the challenge screen.
  mode = "SMS";
  await open();
  loginHandler = () => challenge("delivery-failed", "SMS", false);
  await credentials();
  await page.getByRole("alert").waitFor();
  assert(page.url().includes("/login"));
  // Password reset uses a generic confirmation and the configured CSRF token.
  await open();
  let resetArgs;
  await page.route(
    "**/api/method/frappe.core.doctype.user.user.reset_password",
    (r) => {
      resetArgs = r.request().postDataJSON();
      assert.equal(r.request().headers()["x-frappe-csrf-token"], "mock-csrf");
      return r.fulfill({ json: {} });
    },
  );
  await page
    .getByRole("button", { name: "Forgot password?", exact: true })
    .click();
  await page.getByLabel("Account email").fill("user@example.test");
  await page
    .getByRole("button", { name: "Send reset instructions", exact: false })
    .click();
  await page
    .getByText("If this account is eligible, password reset instructions")
    .waitFor();
  assert.deepEqual(resetArgs, { user: "user@example.test" });
  // Malicious redirects are confined to the portal.
  await open("?redirect-to=https%3A%2F%2Fevil.example");
  loginHandler = () => {
    loggedIn = true;
    return { json: { message: "No App" } };
  };
  await credentials();
  await page.getByRole("heading", { name: "Welcome, Test" }).waitFor();
  assert(page.url().endsWith("/life_portal/"));
  // Forced password reset accepts only the local update-password route.
  await open();
  loginHandler = () => ({
    json: {
      message: "Password Reset",
      redirect_to: "https://evil.example/update-password",
    },
  });
  await credentials();
  await page.getByRole("alert").waitFor();
  assert(page.url().includes("/login"));
  await page.route("**/update-password?**", (r) =>
    r.fulfill({ body: "Password change page" }),
  );
  loginHandler = () => ({
    json: {
      message: "Password Reset",
      redirect_to: "/update-password?key=test-only",
    },
  });
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.waitForURL("**/update-password?key=test-only");
  // Disabled password login and already-signed-in login-page access.
  getContext = () => ({ ...config(), password_login_enabled: false });
  await page.goto(base + "/life_portal/login");
  await page.getByText("Password sign-in is disabled for this site.").waitFor();
  getContext = () => ({ ...config(), authenticated: true });
  loggedIn = true;
  await page.goto(base + "/life_portal/login");
  await page.getByRole("heading", { name: "Welcome, Test" }).waitFor();
  assert.deepEqual(errors, []);
  console.log(
    "PASS: login desktop/mobile; password visibility; bad credentials; direct/bypassed 2FA; ambiguous success rejection; OTP challenge/retry/resend/expiry; authenticator mode; delivery error; password reset; safe redirects; forced reset; password-login-disabled and existing session.",
  );
  await browser.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
