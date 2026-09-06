/* Kaushora app shell — sidebar, topbar, active nav, session chip.
   Injected into every app page via <div id="shell"> + data-page attribute. */
(function () {
  "use strict";

  const NAV_MAIN = [
    ["dashboard.html", "Dashboard", "grid", "dashboard"],
    ["skills.html", "Skills", "pulse", "skills"],
    ["courses.html", "Courses", "book", "courses"],
    ["districts.html", "Districts", "pin", "districts"],
    ["careers.html", "Careers", "case", "careers"],
    ["employers.html", "Employers", "bank", "employers"],
  ];
  const NAV_SYS = [
    ["ai.html", "Kaushora AI", "spark", "ai"],
    ["login.html", "Login", "user", "login"],
  ];

  function navHtml(active) {
    const item = (href, label, ic, key) =>
      '<a href="' + href + '" class="' + (active === key ? "active" : "") + '" ' +
      (active === key ? 'aria-current="page"' : "") + ">" + window.KIcon(ic) +
      "<span>" + label + "</span></a>";
    return (
      '<div class="nav-label">Ontology &amp; Intelligence</div><nav class="nav" aria-label="Primary">' +
      NAV_MAIN.map((n) => item(n[0], n[1], n[2], n[3])).join("") +
      '</nav><div class="nav-label">Analytical Systems</div><nav class="nav" aria-label="Systems">' +
      NAV_SYS.map((n) => item(n[0], n[1], n[2], n[3])).join("") +
      "</nav>"
    );
  }

  function mount(active) {
    const shell = document.getElementById("shell");
    if (!shell) return;
    shell.className = "shell";
    shell.innerHTML =
      '<div class="scrim" id="scrim"></div>' +
      '<aside class="sidebar" aria-label="Kaushora navigation">' +
      '<a class="brand" href="index.html" aria-label="Kaushora home">' +
      '<img src="assets/kaushora-logo.png" alt="Kaushora Labour Intelligence" onerror="this.onerror=null;this.src=\'assets/brand.svg\'" /></a>' +
      '<div class="engine-card"><b><span class="dot"></span>Authoritative Engine</b>' +
      "<span>Coverage: 100% Grounded</span></div>" +
      navHtml(active) +
      '<div class="side-foot"><div class="user-chip" id="userChip">' +
      '<div class="avatar">K</div><div><b>Guest</b><span>Prototype access</span></div>' +
      "</div></div></aside>" +
      '<div class="main"><div class="topbar">' +
      '<button class="icon-btn hamburger" id="hamburger" aria-label="Open navigation">' + window.KIcon("menu") + "</button>" +
      '<span class="dataset-pill" id="dsPill">Authoritative Dataset: <b>checking…</b></span>' +
      '<span class="spacer"></span>' +
      '<a class="icon-btn" href="ai.html" aria-label="Kaushora AI">' + window.KIcon("spark") + "</a>" +
      '<a class="icon-btn" href="login.html" aria-label="Account">' + window.KIcon("user") + "</a>" +
      "</div>" +
      '<div class="page" id="page"></div>' +
      '<div class="page" style="padding-top:0"><div class="evidence-strip" style="opacity:0.9;font-size:12.5px">' + window.KIcon("shield") +
      "<div><b>Kaushora Dataset:</b> Real evidence (NCO 2015, SSC QPs, WEF) + <b>synthetic demo</b> (180 jobs, 4 districts, 24 placements) for feature completeness — all metrics live from backend (<code>/api/…</code>), synthetic rows <code>is_synthetic=1</code>.</div></div></div>" +
      "</div>";
    document.getElementById("scrim").addEventListener("click", () => document.body.classList.remove("nav-open"));
    document.getElementById("hamburger").addEventListener("click", () => document.body.classList.toggle("nav-open"));
    shell.querySelectorAll(".sidebar .nav a").forEach((a) =>
      a.addEventListener("click", () => document.body.classList.remove("nav-open"))
    );
    const fav = document.createElement("link");
    fav.rel = "icon"; fav.type = "image/png"; fav.href = "assets/favicon.png";
    fav.onerror = function () { this.href = "assets/favicon.svg"; this.type = "image/svg+xml"; };
    document.head.appendChild(fav);
    // Keep SVG favicon as fallback for older browsers
    const fav2 = document.createElement("link");
    fav2.rel = "icon"; fav2.type = "image/svg+xml"; fav2.href = "assets/favicon.svg";
    document.head.appendChild(fav2);
    refreshStatus();
    refreshUser();
  }

  async function refreshStatus() {
    const pill = document.getElementById("dsPill");
    if (!pill) return;
    try {
      const ds = await window.KaushoraAPI.dataStatus();
      const c = ds.record_counts;
      pill.innerHTML =
        'Authoritative Dataset: <span class="ok">Active</span> · ' +
        c.skills + " skills · " + c.courses + " courses · " + c.job_roles + " roles";
      pill.title = "Source: data/raw/kaushora_real_evidence_dataset.md · " +
        (ds.last_ingestion ? "ingested " + ds.last_ingestion.started_at : "no ingestion record");
    } catch (e) {
      pill.innerHTML = "Authoritative Dataset: <b>unreachable</b>";
      pill.title = e.message;
    }
  }

  async function refreshUser() {
    try {
      const me = await window.KaushoraAPI.me();
      const chip = document.getElementById("userChip");
      if (chip && me && me.user) {
        const initial = (me.user.email || "U").charAt(0).toUpperCase();
        chip.innerHTML = '<div class="avatar">' + initial + "</div><div><b>" +
          escapeHtml(me.user.email) + "</b><span>" + escapeHtml(me.user.role || "viewer") + "</span></div>";
      }
    } catch (e) { /* stay as guest */ }
  }

  function escapeHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  // Shared render helpers for all pages
  function skeletonCards(n) {
    let h = '<div class="grid kpis" aria-hidden="true">';
    for (let i = 0; i < (n || 5); i++) h += '<div class="card"><div class="skel" style="height:64px"></div></div>';
    return h + "</div>";
  }
  function emptyState(title, msg, icon) {
    return '<div class="empty">' + window.KIcon(icon || "db") + "<h3>" + title + "</h3><p>" + msg + "</p></div>";
  }
  function errorState(msg, retry) {
    return '<div class="error-box">' + window.KIcon("alert") + "<h3>Could not load this view</h3><p>" +
      escapeHtml(msg) + "</p>" +
      (retry ? '<button class="btn ghost sm" onclick="' + retry + '()">Retry</button>' : "") + "</div>";
  }

  window.KShell = { mount, skeletonCards, emptyState, errorState, escapeHtml };
  // Mount the shell as soon as #shell exists. Page scripts run at parse time
  // (before DOMContentLoaded) and need #page to exist immediately; waiting
  // for DOMContentLoaded left `document.getElementById("page")` null and
  // crashed every page with "Cannot set properties of null (innerHTML)".
  // Guarded against double-mount (mount sets shell.className = "shell").
  function boot() {
    const shell = document.getElementById("shell");
    if (shell && !shell.classList.contains("shell")) {
      window.KShell.mount(document.body.getAttribute("data-page") || "");
    }
  }
  boot();
  document.addEventListener("DOMContentLoaded", boot);
})();
