const config = window.SAAS_CONFIG || { appDomain: "app.local" };

function byId(id) {
  return document.getElementById(id);
}

function setText(id, value) {
  const node = byId(id);
  if (node) {
    node.textContent = value;
  }
}

function writeJson(id, value) {
  const node = byId(id);
  if (node) {
    node.textContent = JSON.stringify(value, null, 2);
  }
}

function renderAdminWorkspaces(workspaces) {
  const list = byId("admin-workspaces-list");
  if (!list) {
    return;
  }
  list.innerHTML = "";
  if (!Array.isArray(workspaces) || workspaces.length === 0) {
    const empty = document.createElement("p");
    empty.className = "status-line";
    empty.textContent = "No workspaces available.";
    list.appendChild(empty);
    return;
  }
  workspaces.forEach((workspace) => {
    const row = document.createElement("div");
    row.className = "workspace-admin-row";

    const meta = document.createElement("div");
    meta.className = "workspace-admin-meta";
    meta.innerHTML = `<strong>${workspace.name}</strong><span>${workspace.subdomain}.${config.appDomain}</span>`;

    const form = document.createElement("form");
    form.className = "workspace-admin-form";
    form.method = "post";
    form.action = `/admin/workspaces/${workspace.id}/delete`;

    const button = document.createElement("button");
    button.type = "submit";
    button.className = "button button-ghost";
    button.textContent = "Delete Workspace";

    form.appendChild(button);
    row.appendChild(meta);
    row.appendChild(form);
    list.appendChild(row);
  });
}

function currentPage() {
  return document.body.dataset.page || "";
}

function currentHostIsRootDomain() {
  return window.location.hostname === config.appDomain;
}

function tenantLoginUrl(slug) {
  return `${window.location.protocol}//${slug}.${config.appDomain}/login`;
}

function apiHeaders(token) {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function parseError(payload, fallback) {
  if (payload && typeof payload === "object" && "detail" in payload) {
    return String(payload.detail);
  }
  return fallback;
}

function clearTenantSelection() {
  const panel = byId("tenant-selection-panel");
  const list = byId("tenant-selection-list");
  if (panel) {
    panel.hidden = true;
  }
  if (list) {
    list.innerHTML = "";
  }
}

function renderTenantSelection(title, tenants, email) {
  const panel = byId("tenant-selection-panel");
  const titleNode = byId("tenant-selection-title");
  const list = byId("tenant-selection-list");
  if (!panel || !titleNode || !list) {
    return;
  }
  panel.hidden = false;
  titleNode.textContent = title;
  list.innerHTML = "";
  tenants.forEach((tenant) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "tenant-chip";
    button.innerHTML = `<strong>${tenant.name}</strong><span>${tenant.subdomain}.${config.appDomain}</span>`;
    button.addEventListener("click", async () => {
      if (!email) {
        setText("landing-status", "Enter your email first, then choose a workspace.");
        return;
      }
      try {
        setText("landing-status", `Sending a sign-in link for ${tenant.subdomain}.${config.appDomain}...`);
        const result = await postJson("/api/v1/auth/magic-link/start", {
          email,
          tenant_subdomain: tenant.subdomain,
        });
        setText("landing-status", `A sign-in link has been sent for ${tenant.subdomain}.${config.appDomain}. Check your email to continue.`);
      } catch (error) {
        setText("landing-status", error.message);
      }
    });
    list.appendChild(button);
  });
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  let data = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }
  if (!response.ok) {
    throw new Error(parseError(data, "Request failed"));
  }
  return data;
}

async function getJson(url, token) {
  const response = await fetch(url, {
    headers: apiHeaders(token),
  });
  let data = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }
  if (!response.ok) {
    throw new Error(parseError(data, "Request failed"));
  }
  return data;
}

function saveUserTokens(payload) {
  localStorage.setItem("saas_user_access_token", payload.access_token);
  localStorage.setItem("saas_user_refresh_token", payload.refresh_token);
}

function clearUserTokens() {
  localStorage.removeItem("saas_user_access_token");
  localStorage.removeItem("saas_user_refresh_token");
}

function userAccessToken() {
  return localStorage.getItem("saas_user_access_token");
}

function userRefreshToken() {
  return localStorage.getItem("saas_user_refresh_token");
}

function saveAdminTokens(payload) {
  localStorage.setItem("saas_admin_access_token", payload.access_token);
  localStorage.setItem("saas_admin_refresh_token", payload.refresh_token);
  document.cookie = `saas_admin_access_token=${encodeURIComponent(payload.access_token)}; Path=/; SameSite=Lax${window.location.protocol === "https:" ? "; Secure" : ""}`;
}

function clearAdminTokens() {
  localStorage.removeItem("saas_admin_access_token");
  localStorage.removeItem("saas_admin_refresh_token");
  document.cookie = "saas_admin_access_token=; Path=/; Max-Age=0; SameSite=Lax";
}

function adminAccessToken() {
  return localStorage.getItem("saas_admin_access_token");
}

function adminRefreshToken() {
  return localStorage.getItem("saas_admin_refresh_token");
}

function initLanding() {
  const input = byId("user-entry-email");
  const button = byId("tenant-entry-button");
  if (!input || !button) {
    return;
  }
  button.addEventListener("click", async () => {
    const email = input.value.trim().toLowerCase();
    if (!email) {
      try {
        setText("landing-status", "Loading example workspaces...");
        const data = await getJson("/api/v1/auth/tenant-examples");
        renderTenantSelection(
          "Demo workspaces available for access",
          data.tenants,
          "",
        );
        setText("landing-status", "Enter your email, then choose an example workspace if you need access.");
      } catch (error) {
        setText("landing-status", error.message);
      }
      return;
    }
    clearTenantSelection();
    try {
      setText("landing-status", "Checking your workspace access...");
      const data = await postJson("/api/v1/auth/discover", { email });
      if (data.mode === "single_tenant") {
        setText("landing-status", "A sign-in link has been sent to your email. Open the link to access your workspace.");
        return;
      }
      if (data.mode === "multiple_tenants") {
        setText("landing-status", "Choose the workspace you want to access.");
        renderTenantSelection("Choose one of your workspaces", data.tenants, email);
        return;
      }
      if (data.mode === "no_tenants") {
        setText("landing-status", "No workspace access found for this email. You can request access to an existing workspace or contact your administrator.");
        renderTenantSelection(
          "Select an example workspace to request access. These are prepared environments for access. Your organization may provide a dedicated workspace.",
          data.example_tenants,
          email,
        );
        return;
      }
      setText("landing-status", data.detail);
    } catch (error) {
      setText("landing-status", error.message);
    }
  });
}

function initUserLogin() {
  const form = byId("user-login-form");
  if (!form) {
    return;
  }
  if (currentHostIsRootDomain()) {
    setText("user-login-status", "Open this page on your workspace subdomain, such as team1.app.local.");
  }
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    const payload = {
      email: String(formData.get("email") || ""),
    };
    try {
      setText("user-login-status", "Sending a sign-in link...");
      const data = await postJson("/api/v1/auth/magic-link/start", payload);
      setText("user-login-status", "A sign-in link has been sent to your email. Open the link to access this workspace.");
    } catch (error) {
      setText("user-login-status", error.message);
    }
  });
}

async function loadUserDashboard() {
  const token = userAccessToken();
  if (!token) {
    window.location.href = "/login";
    return;
  }
  try {
    setText("user-dashboard-status", "Loading tenant data...");
    const [me, memberships, subscription, usage] = await Promise.all([
      getJson("/api/v1/me", token),
      getJson("/api/v1/memberships", token),
      getJson("/api/v1/billing/subscription", token),
      getJson("/api/v1/usage", token),
    ]);
    setText("tenant-dashboard-title", `${me.tenant.name} · ${me.role}`);
    writeJson("user-me-output", me);
    writeJson("user-memberships-output", memberships);
    writeJson("user-subscription-output", subscription);
    writeJson("user-usage-output", usage);
    setText("user-dashboard-status", `Tenant host: ${window.location.hostname}`);
  } catch (error) {
    setText("user-dashboard-status", error.message);
  }
}

function initUserDashboard() {
  const refreshButton = byId("user-refresh-button");
  const logoutButton = byId("user-logout-button");
  if (refreshButton) {
    refreshButton.addEventListener("click", loadUserDashboard);
  }
  if (logoutButton) {
    logoutButton.addEventListener("click", async () => {
      const refreshToken = userRefreshToken();
      try {
        if (refreshToken) {
          await postJson("/api/v1/auth/logout", { refresh_token: refreshToken });
        }
      } catch {
      } finally {
        clearUserTokens();
        window.location.href = "/login";
      }
    });
  }
  loadUserDashboard();
}

function initAdminLogin() {
  const form = byId("admin-login-form");
  if (!form) {
    return;
  }
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    const payload = {
      email: String(formData.get("email") || ""),
    };
    try {
      setText("admin-login-status", "Sending an admin sign-in link...");
      const data = await postJson("/api/v1/admin/auth/magic-link/start", payload);
      setText("admin-login-status", "A sign-in link has been sent to your email. Open the link to access the admin console.");
    } catch (error) {
      setText("admin-login-status", error.message);
    }
  });
}

async function completeMagicLink() {
  const params = new URLSearchParams(window.location.search);
  const token = params.get("token");
  const flow = params.get("flow");
  if (!token || !flow) {
    setText("magic-link-status", "Missing sign-in link parameters.");
    return;
  }
  try {
    setText("magic-link-status", "Verifying your sign-in link...");
    if (flow === "user") {
      const data = await postJson("/api/v1/auth/magic-link/consume", { token });
      saveUserTokens(data);
      window.location.href = "/dashboard";
      return;
    }
    if (flow === "admin") {
      const data = await postJson("/api/v1/admin/auth/magic-link/consume", { token });
      saveAdminTokens(data);
      window.location.href = "/admin/dashboard";
      return;
    }
    setText("magic-link-status", "Unsupported magic link flow.");
  } catch (error) {
    setText("magic-link-status", error.message);
  }
}

async function loadAdminDashboard() {
  const token = adminAccessToken();
  if (!token) {
    window.location.href = "/admin/login";
    return;
  }
  try {
    setText("admin-dashboard-status", "Loading platform metrics...");
    const [overview, revenue, tenants] = await Promise.all([
      getJson("/api/v1/admin/metrics/overview", token),
      getJson("/api/v1/admin/metrics/revenue", token),
      getJson("/api/v1/admin/metrics/recent-tenants", token),
    ]);
    writeJson("admin-overview-output", overview);
    writeJson("admin-revenue-output", revenue);
    renderAdminWorkspaces(tenants);
    const params = new URLSearchParams(window.location.search);
    const workspaceCreated = params.get("workspace_created");
    const workspaceName = params.get("workspace_name");
    const workspaceDeleted = params.get("workspace_deleted");
    const workspaceDeleteError = params.get("workspace_delete_error");
    if (workspaceDeleteError) {
      setText("admin-dashboard-status", workspaceDeleteError);
    } else if (workspaceDeleted) {
      setText("admin-dashboard-status", `Workspace ${workspaceDeleted} deleted.`);
    } else if (workspaceCreated && workspaceName) {
      setText("admin-dashboard-status", `Workspace ${workspaceName} created at ${workspaceCreated}.${config.appDomain}`);
    } else {
      setText("admin-dashboard-status", `Admin host: ${window.location.hostname}`);
    }
  } catch (error) {
    setText("admin-dashboard-status", error.message);
  }
}

function initAdminDashboard() {
  const refreshButton = byId("admin-refresh-button");
  const logoutButton = byId("admin-logout-button");
  if (refreshButton) {
    refreshButton.addEventListener("click", loadAdminDashboard);
  }
  if (logoutButton) {
    logoutButton.addEventListener("click", async () => {
      const refreshToken = adminRefreshToken();
      try {
        if (refreshToken) {
          await postJson("/api/v1/admin/auth/logout", { refresh_token: refreshToken });
        }
      } catch {
      } finally {
        clearAdminTokens();
        window.location.href = "/admin/login";
      }
    });
  }
  loadAdminDashboard();
}

document.addEventListener("DOMContentLoaded", () => {
  const page = currentPage();
  if (page === "landing") {
    initLanding();
  } else if (page === "user-login") {
    initUserLogin();
  } else if (page === "user-dashboard") {
    initUserDashboard();
  } else if (page === "admin-login") {
    initAdminLogin();
  } else if (page === "admin-dashboard") {
    initAdminDashboard();
  } else if (page === "magic-link-complete") {
    completeMagicLink();
  }
});
