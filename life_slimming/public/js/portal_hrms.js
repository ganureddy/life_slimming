/* Adapt the imported HRMS screen to the portal's single-sidebar layout. */
(() => {
  "use strict";
  document.documentElement.classList.add("portal-hrms");
  const mast = document.querySelector(".mast");
  const originalNav = document.getElementById("nav");
  const workspace = document.querySelector(".app");
  if (!mast || !originalNav || !workspace) return;

  const status = document.createElement("div");
  status.className = "portal-hrms-status";
  status.setAttribute("role", "status");
  status.textContent = "Loading HR workspace...";
  mast.after(status);
  workspace.inert = true;

  const picker = document.createElement("details");
  picker.className = "portal-hrms-picker";
  const summary = document.createElement("summary");
  summary.textContent = "All HR sections";
  const menu = document.createElement("div");
  menu.className = "portal-hrms-menu";
  const search = document.createElement("input");
  search.type = "search";
  search.placeholder = "Find an HR section";
  search.setAttribute("aria-label", "Find an HR section");
  const results = document.createElement("div");
  results.className = "portal-hrms-results";
  menu.append(search, results);
  picker.append(summary, menu);
  mast.append(picker);

  const shortcuts = document.createElement("nav");
  shortcuts.className = "portal-hrms-tabs";
  shortcuts.setAttribute("aria-label", "HR sections");
  status.after(shortcuts);
  const quickViews = { dash: "Overview", emps: "Employees", attend: "Attendance", leave: "Leave", reports: "Reports & payroll" };
  let entries = [];

  function syncNavigation() {
    const active = window.V;
    document.documentElement.dataset.hrmsView = active;
    shortcuts.querySelectorAll("button").forEach(button => {
      if (button.dataset.view === active) button.setAttribute("aria-current", "page");
      else button.removeAttribute("aria-current");
    });
    results.querySelectorAll("button").forEach(button => {
      if (button.dataset.view === active) button.setAttribute("aria-current", "page");
      else button.removeAttribute("aria-current");
    });
    const current = entries.find(entry => entry.view === active);
    summary.textContent = current ? current.label : "All HR sections";
  }

  function selectEntry(entry) {
    picker.open = false;
    entry.anchor.click();
    syncNavigation();
  }

  function renderMenu() {
    results.replaceChildren();
    const query = search.value.trim().toLowerCase();
    let previousGroup;
    for (const entry of entries) {
      if (!`${entry.label} ${entry.group}`.toLowerCase().includes(query)) continue;
      if (entry.group !== previousGroup) {
        const heading = document.createElement("div");
        heading.className = "portal-hrms-group";
        heading.textContent = entry.group;
        results.append(heading);
        previousGroup = entry.group;
      }
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = entry.label;
      button.dataset.view = entry.view;
      button.addEventListener("click", () => selectEntry(entry));
      results.append(button);
    }
    if (!results.childElementCount) results.textContent = "No matching HR sections";
    syncNavigation();
  }

  function rebuildNavigation() {
    entries = Array.from(originalNav.querySelectorAll(".ngrp")).flatMap(group => {
      const label = group.querySelector(".ghead b")?.textContent || "HR";
      return Array.from(group.querySelectorAll("a")).map(anchor => ({
        anchor,
        group: label,
        view: anchor.dataset.v || "ess",
        label: anchor.querySelector(".nav-title")?.textContent || Array.from(anchor.childNodes)
          .filter(node => node.nodeType === Node.TEXT_NODE).map(node => node.textContent).join("").trim(),
      }));
    });
    shortcuts.replaceChildren();
    for (const [view, label] of Object.entries(quickViews)) {
      const entry = entries.find(item => item.view === view);
      if (!entry) continue;
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = label;
      button.dataset.view = view;
      button.addEventListener("click", () => selectEntry(entry));
      shortcuts.append(button);
    }
    renderMenu();
  }

  search.addEventListener("input", renderMenu);
  picker.addEventListener("toggle", () => {
    if (picker.open) { search.value = ""; renderMenu(); search.focus(); }
  });
  document.addEventListener("click", event => {
    if (!picker.contains(event.target)) picker.open = false;
  });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && picker.open) { picker.open = false; summary.focus(); }
  });
  new MutationObserver(rebuildNavigation).observe(originalNav, { childList: true });

  const originalGo = window.go;
  // The imported payroll patch updates rReports after the render map is built.
  if (window.RENDER && typeof window.rReports === "function") {
    window.RENDER.reports = (...args) => window.rReports(...args);
  }
  window.go = function (...args) {
    const result = originalGo.apply(this, args);
    syncNavigation();
    return result;
  };
  const originalBoot = window.bootApp;
  function finishBoot() {
    rebuildNavigation();
    const defaults = { employees: "dash", attend: "attend", payroll: "reports" };
    const requested = new URLSearchParams(location.search).get("hr_view");
    const view = requested || defaults[window.lifePortalModule.module] || "dash";
    if (entries.some(entry => entry.view === view)) window.go(view, false);
    status.hidden = true;
    workspace.inert = false;
    mast.inert = false;
  }
  window.bootApp = function (...args) {
    const result = originalBoot.apply(this, args);
    finishBoot();
    return result;
  };
  mast.inert = true;

  // The source reports bootstrap failures inside its hidden lock screen.
  const lockMessage = document.getElementById("lockmsg");
  const showFailure = () => {
    if (!lockMessage?.classList.contains("err")) return;
    status.hidden = false;
    status.setAttribute("role", "alert");
    const message = document.createElement("span");
    message.textContent = "HR records could not be loaded. Please retry.";
    const retry = document.createElement("button");
    retry.type = "button";
    retry.textContent = "Retry";
    retry.addEventListener("click", () => location.reload());
    status.replaceChildren(message, retry);
  };
  if (lockMessage) new MutationObserver(showFailure).observe(lockMessage, { attributes: true, childList: true, subtree: true });
  showFailure();
  // A fast bootstrap can finish while the browser parses later source scripts.
  if (window.ME && document.getElementById("wrap")?.childElementCount && !lockMessage?.classList.contains("err")) finishBoot();

  document.getElementById("gq")?.setAttribute("aria-label", "Search employees");
  if (document.getElementById("gq")) document.getElementById("gq").placeholder = "Search employees";
  for (const [id, label] of Object.entries({ brsel: "Branch", dpsel: "Department", stsel: "Employee status" })) {
    document.getElementById(id)?.setAttribute("aria-label", label);
  }
})();
