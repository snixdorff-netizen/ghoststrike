const state = {
  token: window.localStorage.getItem("ada_iq_token"),
  user: null,
  projects: [],
  selectedProjectId: null,
  selectedSnapshot: null,
  agents: [],
  architecture: null,
  access: null,
  adminUsers: [],
  adminProjects: [],
  invitations: [],
};

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const response = await fetch(path, { ...options, headers });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || "Request failed");
  }
  const contentType = response.headers.get("content-type") || "";
  return contentType.includes("application/json") ? response.json() : response.text();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function isOwner(snapshot) {
  return Boolean(state.user && snapshot && snapshot.project.owner_user_id === state.user.user_id);
}

function canWrite(snapshot) {
  if (!state.user || !snapshot) return false;
  if (isOwner(snapshot)) return true;
  return (snapshot.collaborators || []).some(
    (collaborator) => collaborator.user_id === state.user.user_id && collaborator.access_role === "EDITOR",
  );
}

function byNewest(items, field) {
  return [...items].sort((left, right) => String(right[field] || "").localeCompare(String(left[field] || "")));
}

function renderAuth() {
  const loggedIn = Boolean(state.user);
  const registrationOpen = state.access ? state.access.open_registration : true;
  document.getElementById("auth-status").textContent = loggedIn
    ? `Logged in as ${state.user.email} (${state.user.role})`
    : "Not logged in.";
  document.getElementById("logout-button").classList.toggle("hidden", !loggedIn);
  document.getElementById("create-form").classList.toggle("hidden", !loggedIn);
  document.getElementById("create-locked").classList.toggle("hidden", loggedIn);
  document.getElementById("accept-invitation-form").classList.toggle("hidden", !loggedIn);
  document.getElementById("register-form").classList.toggle("hidden", !registrationOpen);
  document.getElementById("admin-panel").classList.toggle("hidden", !loggedIn || state.user.role !== "ADMIN");
}

function renderProjects() {
  const container = document.getElementById("project-list");
  if (!state.user) {
    container.innerHTML = '<div class="empty-state">Log in to view your projects.</div>';
    return;
  }
  if (!state.projects.length) {
    container.innerHTML = '<div class="empty-state">No projects yet. Create one above.</div>';
    return;
  }
  container.innerHTML = state.projects
    .map((project) => {
      const sharedLabel = project.owner_user_id === state.user.user_id ? "Owned" : "Shared";
      return `<article class="project-item ${project.project_id === state.selectedProjectId ? "active" : ""}" data-project-id="${project.project_id}">
        <h3>${escapeHtml(project.name)}</h3>
        <p class="small">${escapeHtml(project.current_phase)} · ${escapeHtml(project.status)} · ${sharedLabel}</p>
        <p>${escapeHtml(project.brief.slice(0, 120))}${project.brief.length > 120 ? "..." : ""}</p>
      </article>`;
    })
    .join("");
  container.querySelectorAll("[data-project-id]").forEach((node) => {
    node.addEventListener("click", () => selectProject(node.dataset.projectId));
  });
}

function renderOutputs(outputs) {
  const container = document.getElementById("outputs");
  container.innerHTML = outputs.length
    ? outputs.map((output) => `<article class="card">
        <h4>${escapeHtml(output.data.agent.display_name)}</h4>
        <p class="small">${escapeHtml(output.output_type)} · confidence ${escapeHtml(output.confidence_score)}</p>
        <p>${escapeHtml(output.data.summary || "No summary available.")}</p>
        <p class="small">Questions: ${escapeHtml((output.data.recommended_questions || []).join(" | "))}</p>
      </article>`).join("")
    : '<div class="empty-state">No outputs yet. Run the current phase.</div>';
}

function renderMessages(runs, messages) {
  const container = document.getElementById("messages");
  const cards = [
    ...byNewest(runs || [], "created_at").map((run) => `<article class="card">
      <div class="pill">${escapeHtml(run.status)}</div>
      <p><strong>${escapeHtml(run.phase)}</strong> · ${escapeHtml(run.summary)}</p>
      <p class="small">${escapeHtml(run.triggered_by)} · ${escapeHtml(run.created_at)}</p>
    </article>`),
    ...byNewest(messages || [], "timestamp").map((message) => `<article class="card">
      <div class="pill">${escapeHtml(message.message_type)}</div>
      <p><strong>${escapeHtml(message.sender)}</strong> to <strong>${escapeHtml(message.receiver)}</strong></p>
      <p class="small">${escapeHtml(message.step)} · ${escapeHtml(message.phase)}</p>
    </article>`),
  ];
  container.innerHTML = cards.join("") || '<div class="empty-state">No messages yet.</div>';
}

function renderCollaborators(snapshot) {
  const collaborators = snapshot.collaborators || [];
  document.getElementById("collaborator-list").innerHTML = collaborators.length
    ? collaborators.map((collaborator) => `<article class="card">
        <p><strong>${escapeHtml(collaborator.user_id)}</strong></p>
        <p class="small">${escapeHtml(collaborator.access_role)}</p>
      </article>`).join("")
    : '<div class="empty-state">No collaborators yet.</div>';

  document.getElementById("invitation-list").innerHTML = state.invitations.length
    ? state.invitations.map((invitation) => `<article class="card">
        <p><strong>${escapeHtml(invitation.invited_email)}</strong></p>
        <p class="small">${escapeHtml(invitation.access_role)} · ${escapeHtml(invitation.status)}</p>
        <p class="small">Token: ${escapeHtml(invitation.token)}</p>
      </article>`).join("")
    : '<div class="empty-state">No invitations yet.</div>';

  document.getElementById("invite-form").classList.toggle("hidden", !isOwner(snapshot));
}

function renderFeedback(snapshot) {
  const feedback = byNewest(snapshot.feedback || [], "timestamp");
  document.getElementById("feedback-list").innerHTML = feedback.length
    ? feedback.map((item) => `<article class="card">
        <div class="pill">${escapeHtml(item.data.category || "GENERAL")}</div>
        <p>${escapeHtml(item.message)}</p>
        <p class="small">${escapeHtml(item.data.actor || "system")} · ${escapeHtml(item.timestamp)}</p>
      </article>`).join("")
    : '<div class="empty-state">No alpha feedback yet.</div>';
}

function renderOperations(snapshot) {
  const jobs = byNewest(snapshot.jobs || [], "created_at");
  const events = byNewest(snapshot.events || [], "timestamp");

  document.getElementById("jobs").innerHTML = jobs.length
    ? jobs.map((job) => `<article class="card">
        <div class="pill">${escapeHtml(job.status)}</div>
        <p><strong>${escapeHtml(job.phase)}</strong> · ${escapeHtml(job.job_type)}</p>
        <p class="small">${escapeHtml(job.requested_by)} · ${escapeHtml(job.created_at)}</p>
        ${job.error ? `<p class="small">${escapeHtml(job.error)}</p>` : ""}
      </article>`).join("")
    : '<div class="empty-state">No queued jobs yet.</div>';

  document.getElementById("events").innerHTML = events.length
    ? events.map((event) => `<article class="card">
        <div class="pill">${escapeHtml(event.level)}</div>
        <p><strong>${escapeHtml(event.event_type)}</strong></p>
        <p>${escapeHtml(event.message)}</p>
        <p class="small">${escapeHtml(event.data.actor || "system")} · ${escapeHtml(event.timestamp)}</p>
      </article>`).join("")
    : '<div class="empty-state">No events yet.</div>';
}

function renderProjectDetail() {
  const emptyState = document.getElementById("empty-state");
  const detail = document.getElementById("project-detail");
  if (!state.user || !state.selectedSnapshot) {
    emptyState.classList.remove("hidden");
    emptyState.textContent = state.user ? "Select a project to inspect its workflow." : "Log in to inspect workflow details.";
    detail.classList.add("hidden");
    return;
  }

  const snapshot = state.selectedSnapshot;
  const { project, outputs, messages, runs } = snapshot;
  const writable = canWrite(snapshot);

  emptyState.classList.add("hidden");
  detail.classList.remove("hidden");

  document.getElementById("detail-phase").textContent = project.current_phase;
  document.getElementById("detail-status").textContent = project.status;
  document.getElementById("detail-gate").textContent = project.gate.status;
  document.getElementById("detail-owner").textContent = project.owner_user_id;
  document.getElementById("detail-brief").textContent = project.brief;

  document.getElementById("run-phase-button").disabled = !writable;
  document.getElementById("queue-phase-button").disabled = !writable;
  document.getElementById("run-v1-button").disabled = !writable;
  document.getElementById("run-full-cycle-button").disabled = !writable;
  document.getElementById("approve-button").disabled = !writable;
  document.getElementById("reject-button").disabled = !writable;

  renderOutputs(outputs || []);
  renderMessages(runs || [], messages || []);
  renderCollaborators(snapshot);
  renderFeedback(snapshot);
  renderOperations(snapshot);
}

function renderMetadata() {
  document.getElementById("agent-roster").innerHTML = state.agents
    .map((agent) => `<article class="card">
      <h4>${escapeHtml(agent.code_name)}</h4>
      <p class="small">${escapeHtml(agent.display_name)} · ${escapeHtml(agent.phase)}</p>
      <p>${escapeHtml(agent.description)}</p>
    </article>`)
    .join("");

  document.getElementById("architecture-summary").innerHTML = state.architecture
    ? `<article class="card">
        <h4>Sprint ${escapeHtml(state.architecture.sprint)}</h4>
        <p>${state.architecture.capabilities.map(escapeHtml).join("<br />")}</p>
        <p class="small">API: ${escapeHtml(state.architecture.tech_stack.api)}<br />Store: ${escapeHtml(state.architecture.tech_stack.persistence)}<br />UI: ${escapeHtml(state.architecture.tech_stack.frontend)}</p>
      </article>`
    : "";
}

function renderAdminPanel() {
  if (!state.user || state.user.role !== "ADMIN") return;
  document.getElementById("admin-users").innerHTML = state.adminUsers.length
    ? state.adminUsers.map((user) => `<article class="card">
        <p><strong>${escapeHtml(user.email)}</strong></p>
        <p class="small">${escapeHtml(user.role)} · ${escapeHtml(user.user_id)}</p>
      </article>`).join("")
    : '<div class="empty-state">No users found.</div>';

  document.getElementById("admin-projects").innerHTML = state.adminProjects.length
    ? state.adminProjects.map((project) => `<article class="card">
        <p><strong>${escapeHtml(project.name)}</strong></p>
        <p class="small">${escapeHtml(project.owner_user_id)} · ${escapeHtml(project.current_phase)} · ${escapeHtml(project.status)}</p>
      </article>`).join("")
    : '<div class="empty-state">No projects found.</div>';
}

async function loadProjects() {
  if (!state.user) {
    state.projects = [];
    state.selectedSnapshot = null;
    renderProjects();
    renderProjectDetail();
    return;
  }
  state.projects = await api("/projects");
  renderProjects();
}

async function loadAdminData() {
  if (!state.user || state.user.role !== "ADMIN") {
    state.adminUsers = [];
    state.adminProjects = [];
    return;
  }
  [state.adminUsers, state.adminProjects] = await Promise.all([api("/admin/users"), api("/admin/projects")]);
  renderAdminPanel();
}

async function loadMetadata() {
  [state.agents, state.architecture, state.access] = await Promise.all([api("/meta/agents"), api("/meta/architecture"), api("/meta/access")]);
  renderMetadata();
  renderAuth();
}

async function loadCurrentUser() {
  if (!state.token) {
    state.user = null;
    renderAuth();
    return;
  }
  try {
    state.user = await api("/me");
  } catch (_error) {
    state.token = null;
    state.user = null;
    window.localStorage.removeItem("ada_iq_token");
  }
  renderAuth();
}

async function loadProjectSharing(projectId) {
  state.invitations = [];
  if (!state.user || !state.selectedSnapshot) return;
  try {
    if (isOwner(state.selectedSnapshot)) {
      state.invitations = await api(`/projects/${projectId}/invitations`);
    }
  } catch (_error) {
    state.invitations = [];
  }
}

async function selectProject(projectId) {
  state.selectedProjectId = projectId;
  state.selectedSnapshot = await api(`/projects/${projectId}`);
  await loadProjectSharing(projectId);
  renderProjects();
  renderProjectDetail();
}

async function refreshSelectedProject() {
  if (!state.selectedProjectId) return;
  await selectProject(state.selectedProjectId);
}

async function submitAuth(path, email, password) {
  const response = await api(path, { method: "POST", body: JSON.stringify({ email, password }) });
  state.token = response.token;
  state.user = response.user;
  window.localStorage.setItem("ada_iq_token", state.token);
  renderAuth();
  await Promise.all([loadProjects(), loadAdminData()]);
  renderProjectDetail();
}

async function createProject(event) {
  event.preventDefault();
  const snapshot = await api("/projects", {
    method: "POST",
    body: JSON.stringify({
      name: document.getElementById("project-name").value,
      brief: document.getElementById("project-brief").value,
    }),
  });
  document.getElementById("create-form").reset();
  await Promise.all([loadProjects(), loadAdminData()]);
  state.selectedProjectId = snapshot.project.project_id;
  state.selectedSnapshot = snapshot;
  await loadProjectSharing(snapshot.project.project_id);
  renderProjects();
  renderProjectDetail();
}

async function runCurrentPhase() {
  if (!state.selectedProjectId) return;
  state.selectedSnapshot = await api(`/projects/${state.selectedProjectId}/start`, { method: "POST" });
  await Promise.all([loadProjects(), loadAdminData()]);
  await loadProjectSharing(state.selectedProjectId);
  renderProjectDetail();
}

async function queueCurrentPhase() {
  if (!state.selectedProjectId) return;
  const job = await api(`/projects/${state.selectedProjectId}/queue`, { method: "POST" });
  await refreshSelectedProject();
  window.alert(`Queued ${job.phase} as job ${job.job_id}. Start the worker to process it.`);
}

async function runV1Package() {
  if (!state.selectedProjectId) return;
  const result = await api(`/projects/${state.selectedProjectId}/flows/v1-package`, {
    method: "POST",
    body: JSON.stringify({ approval_feedback: "Proceed" }),
  });
  await refreshSelectedProject();
  await Promise.all([loadProjects(), loadAdminData()]);
  window.alert(`V1 package complete with ${result.included_outputs.length} outputs.`);
}

async function runFullCycle() {
  if (!state.selectedProjectId) return;
  const result = await api(`/projects/${state.selectedProjectId}/flows/full-cycle`, {
    method: "POST",
    body: JSON.stringify({ approval_feedback: "Proceed" }),
  });
  await refreshSelectedProject();
  await Promise.all([loadProjects(), loadAdminData()]);
  window.alert(`Full cycle complete with ${result.included_outputs.length} outputs.`);
}

async function submitDecision(approved) {
  if (!state.selectedProjectId) return;
  state.selectedSnapshot = await api(`/projects/${state.selectedProjectId}/decision`, {
    method: "POST",
    body: JSON.stringify({ approved, feedback: document.getElementById("decision-feedback").value }),
  });
  await Promise.all([loadProjects(), loadAdminData()]);
  await loadProjectSharing(state.selectedProjectId);
  renderProjectDetail();
}

async function createInvitation(event) {
  event.preventDefault();
  if (!state.selectedProjectId) return;
  await api(`/projects/${state.selectedProjectId}/invitations`, {
    method: "POST",
    body: JSON.stringify({
      email: document.getElementById("invite-email").value,
      access_role: document.getElementById("invite-role").value,
    }),
  });
  document.getElementById("invite-form").reset();
  await loadProjectSharing(state.selectedProjectId);
  await refreshSelectedProject();
}

async function acceptInvitation(event) {
  event.preventDefault();
  await api("/invitations/accept", {
    method: "POST",
    body: JSON.stringify({ token: document.getElementById("invitation-token").value }),
  });
  document.getElementById("accept-invitation-form").reset();
  await Promise.all([loadProjects(), loadAdminData()]);
  renderProjects();
  window.alert("Invitation accepted.");
}

async function createAdminUser(event) {
  event.preventDefault();
  await api("/admin/users", {
    method: "POST",
    body: JSON.stringify({
      email: document.getElementById("admin-create-email").value,
      password: document.getElementById("admin-create-password").value,
      role: document.getElementById("admin-create-role").value,
    }),
  });
  document.getElementById("admin-create-user-form").reset();
  await loadAdminData();
  window.alert("Alpha user created.");
}

async function submitProjectFeedback(event) {
  event.preventDefault();
  if (!state.selectedProjectId) return;
  await api(`/projects/${state.selectedProjectId}/feedback`, {
    method: "POST",
    body: JSON.stringify({
      summary: document.getElementById("feedback-summary").value,
      category: document.getElementById("feedback-category").value,
    }),
  });
  document.getElementById("feedback-form").reset();
  await refreshSelectedProject();
}

function bindEvents() {
  document.getElementById("login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await submitAuth("/auth/login", document.getElementById("login-email").value, document.getElementById("login-password").value);
    } catch (error) {
      window.alert(error.message);
    }
  });

  document.getElementById("register-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await submitAuth("/auth/register", document.getElementById("register-email").value, document.getElementById("register-password").value);
    } catch (error) {
      window.alert(error.message);
    }
  });

  document.getElementById("logout-button").addEventListener("click", async () => {
    try {
      await api("/auth/logout", { method: "POST" });
    } catch (_error) {}
    state.token = null;
    state.user = null;
    state.projects = [];
    state.selectedProjectId = null;
    state.selectedSnapshot = null;
    state.adminUsers = [];
    state.adminProjects = [];
    state.invitations = [];
    window.localStorage.removeItem("ada_iq_token");
    renderAuth();
    renderProjects();
    renderProjectDetail();
    renderAdminPanel();
  });

  document.getElementById("create-form").addEventListener("submit", async (event) => {
    try {
      await createProject(event);
    } catch (error) {
      window.alert(error.message);
    }
  });

  document.getElementById("admin-create-user-form").addEventListener("submit", async (event) => {
    try {
      await createAdminUser(event);
    } catch (error) {
      window.alert(error.message);
    }
  });

  document.getElementById("accept-invitation-form").addEventListener("submit", async (event) => {
    try {
      await acceptInvitation(event);
    } catch (error) {
      window.alert(error.message);
    }
  });

  document.getElementById("invite-form").addEventListener("submit", async (event) => {
    try {
      await createInvitation(event);
    } catch (error) {
      window.alert(error.message);
    }
  });

  document.getElementById("feedback-form").addEventListener("submit", async (event) => {
    try {
      await submitProjectFeedback(event);
    } catch (error) {
      window.alert(error.message);
    }
  });

  document.getElementById("refresh-button").addEventListener("click", async () => {
    try {
      await refreshSelectedProject();
    } catch (error) {
      window.alert(error.message);
    }
  });

  document.getElementById("run-phase-button").addEventListener("click", async () => {
    try {
      await runCurrentPhase();
    } catch (error) {
      window.alert(error.message);
    }
  });

  document.getElementById("queue-phase-button").addEventListener("click", async () => {
    try {
      await queueCurrentPhase();
    } catch (error) {
      window.alert(error.message);
    }
  });

  document.getElementById("run-v1-button").addEventListener("click", async () => {
    try {
      await runV1Package();
    } catch (error) {
      window.alert(error.message);
    }
  });

  document.getElementById("run-full-cycle-button").addEventListener("click", async () => {
    try {
      await runFullCycle();
    } catch (error) {
      window.alert(error.message);
    }
  });

  document.getElementById("approve-button").addEventListener("click", async () => {
    try {
      await submitDecision(true);
    } catch (error) {
      window.alert(error.message);
    }
  });

  document.getElementById("reject-button").addEventListener("click", async () => {
    try {
      await submitDecision(false);
    } catch (error) {
      window.alert(error.message);
    }
  });
}

async function boot() {
  bindEvents();
  await Promise.all([loadMetadata(), loadCurrentUser()]);
  await Promise.all([loadProjects(), loadAdminData()]);
  renderProjectDetail();
}

boot().catch((error) => window.alert(error.message));
