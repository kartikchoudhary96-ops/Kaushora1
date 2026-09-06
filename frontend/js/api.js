/* Kaushora central API client — every page uses this; no duplicated fetch logic,
   no hardcoded application data. All numbers come from the backend. */
(function () {
  "use strict";

  async function req(path, opts) {
    opts = opts || {};
    let res;
    try {
      res = await fetch(path, Object.assign({ headers: { "Content-Type": "application/json" } }, opts));
    } catch (e) {
      throw new Error("Cannot reach the Kaushora backend (" + e.message + "). Is the server running?");
    }
    let body = null;
    try { body = await res.json(); } catch (e) { /* non-JSON */ }
    if (!res.ok) {
      const msg = (body && (body.error || body.message)) || ("Request failed (" + res.status + ")");
      const err = new Error(msg);
      err.status = res.status;
      throw err;
    }
    return body;
  }

  const get = (path) => req(path);
  const post = (path, data) => req(path, { method: "POST", body: JSON.stringify(data || {}) });

  // Unwrap Part-1 envelope {success, data, error} where present; pass through otherwise.
  function unwrap(body) {
    if (body && typeof body === "object" && "success" in body && "data" in body) return body.data;
    return body;
  }

  const cache = {};
  async function cached(key, fn) {
    if (!(key in cache)) cache[key] = fn();
    try { return await cache[key]; }
    catch (e) { delete cache[key]; throw e; }
  }

  window.KaushoraAPI = {
    get, post, unwrap,
    health: () => get("/api/health"),
    dataStatus: () => cached("ds", () => get("/api/data/status").then(unwrap)),
    overview: () => cached("ov", () => get("/api/dashboard/overview").then(unwrap)),
    demand: () => cached("dm", () => get("/api/dashboard/demand").then(unwrap)),
    trends: () => cached("tr", () => get("/api/dashboard/trends").then(unwrap)),
    skills: (params) => get("/api/skills" + (params || "")),
    skill: (id) => get("/api/skills/" + encodeURIComponent(id)),
    skillDemand: (id) => get("/api/skills/" + encodeURIComponent(id) + "/demand"),
    skillGap: (id) => get("/api/skills/" + encodeURIComponent(id) + "/gap"),
    sectors: () => cached("sec", () => get("/api/sectors")),
    roles: () => cached("roles", () => get("/api/roles")),
    careerRoles: () => cached("cr", () => get("/api/careers/roles")),
    courses: () => cached("courses", () => get("/api/courses")),
    course: (id) => get("/api/courses/" + encodeURIComponent(id)),
    courseAlignment: (id) => get("/api/courses/" + encodeURIComponent(id) + "/alignment"),
    districts: () => get("/api/districts"),
    district: (id) => get("/api/districts/" + encodeURIComponent(id)),
    analyzeCareer: (payload) => post("/api/careers/analyze", payload),
    employerSurvey: (payload) => post("/api/employers/survey", payload),
    employerRequirements: () => get("/api/employers/requirements"),
    aiChat: (question) => post("/api/ai/chat", { question }),
    login: (email, password) => post("/api/auth/login", { email, password }),
    logout: () => post("/api/auth/logout", {}),
    me: async () => { try { return await get("/api/auth/me"); } catch (e) { return { user: null }; } },
  };
})();
