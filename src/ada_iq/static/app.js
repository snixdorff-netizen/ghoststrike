const SAMPLE_BRIEF = {
  name: "GhostStrike Alpha Launch Copilot",
  brief:
    "GhostStrike is preparing a 10-user alpha for a browser-based AI product-development platform that guides teams through a structured workflow from problem framing to concept generation, evaluation, launch planning, and measurement. The immediate goal is to validate whether early users can understand the workflow, trust the outputs, and complete a meaningful project without guided onboarding. Focus on small business founders, operators, and innovation leads. Optimize for clarity, useful summaries, visible next steps, and a first session that can be completed in 15 to 25 minutes.",
};

const state = {
  token: window.localStorage.getItem("ada_iq_token"),
  user: null,
  projects: [],
  selectedProjectId: null,
  selectedSnapshot: null,
  agents: [],
  architecture: null,
  access: null,
  adminDashboard: null,
  adminUsers: [],
  adminProjects: [],
  invitations: [],
  projectSearch: "",
  projectFilter: "ALL",
};

const PHASES = ["EMPATHIZE", "IDEATE", "EVALUATE", "REALIZE", "MEASURE"];

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

function showNotice(message, level = "info") {
  const notice = document.getElementById("app-notice");
  notice.textContent = message;
  notice.className = `notice ${level}`;
}

function clearNotice() {
  const notice = document.getElementById("app-notice");
  notice.textContent = "";
  notice.className = "notice hidden";
}

function ownerLabel(project) {
  if (!project) return "";
  if (state.user && project.owner_user_id === state.user.user_id) return "You";
  return project.owner_email || project.owner_user_id;
}

function projectPriority(project) {
  if (project.gate.status === "PENDING") return { label: "Needs Review", className: "needs-review" };
  if (project.status === "COMPLETED") return { label: "Completed", className: "completed" };
  return { label: "In Progress", className: "active" };
}

function renderWorkspaceEmptyState() {
  const emptyState = document.getElementById("empty-state");
  if (!state.user) {
    emptyState.innerHTML = `<div class="empty-state-inner">
      <h3>Log in to start your first GhostStrike workflow.</h3>
      <p>Once you log in, you can create a project, accept a shared invitation, or use the sample brief to test the full product flow.</p>
      <div class="starter-grid">
        <article class="starter-card">
          <strong>1. Access</strong>
          <p>Use the credentials provided by the GhostStrike team or the demo login if it is enabled.</p>
        </article>
        <article class="starter-card">
          <strong>2. Create</strong>
          <p>Start with the sample brief if you want a fast first run instead of writing your own product brief.</p>
        </article>
        <article class="starter-card">
          <strong>3. Run</strong>
          <p>Use V1 Package for the fastest end-to-end evaluation and review the gate when it opens.</p>
        </article>
      </div>
      <div class="starter-actions">
        <button type="button" class="ghost" id="empty-demo-button">Use Demo Login</button>
        <button type="button" class="ghost" id="empty-sample-brief-button">Load Sample Brief</button>
      </div>
    </div>`;
    document.getElementById("empty-demo-button")?.classList.toggle("hidden", !(state.access && state.access.demo_account_enabled));
    document.getElementById("empty-demo-button")?.addEventListener("click", fillDemoLogin);
    document.getElementById("empty-sample-brief-button")?.addEventListener("click", fillSampleBrief);
    return;
  }

  const hasProjects = state.projects.length > 0;
  emptyState.innerHTML = `<div class="empty-state-inner">
    <h3>${hasProjects ? "Select a project to inspect its workflow." : "Create your first project to begin."}</h3>
    <p>${hasProjects
      ? "Choose a project from the left to review outputs, run the next step, or make a gate decision."
      : "Use the sample project to run a fast end-to-end test, or create a custom project from your own brief."}</p>
    <div class="starter-grid">
      <article class="starter-card">
        <strong>Fastest path</strong>
        <p>Create the sample project and run V1 Package. That gives you the strongest first-session demo in a few clicks.</p>
      </article>
      <article class="starter-card">
        <strong>Shared work</strong>
        <p>Paste an invitation token after login if someone shared a project with you.</p>
      </article>
      <article class="starter-card">
        <strong>Decision points</strong>
        <p>When a gate opens, review the outputs, add notes, then approve or reject the project direction.</p>
      </article>
    </div>
    <div class="starter-actions">
      <button type="button" id="empty-create-sample-button">Create Sample Project</button>
      <button type="button" class="ghost" id="empty-load-sample-button">Load Sample Brief</button>
    </div>
  </div>`;
  document.getElementById("empty-create-sample-button")?.addEventListener("click", createSampleProjectFromTemplate);
  document.getElementById("empty-load-sample-button")?.addEventListener("click", fillSampleBrief);
}

function actionState(snapshot) {
  if (!snapshot || !state.user) {
    return {
      canRunPhase: false,
      canQueuePhase: false,
      canRunPackage: false,
      canRunFullCycle: false,
      canDecide: false,
      hint: "Log in and select a project to begin.",
    };
  }

  const { project } = snapshot;
  const writable = canWrite(snapshot);
  const gatePending = project.gate.status === "PENDING";
  const atStart = project.current_phase === "EMPATHIZE" && project.status === "DRAFT";
  const completed = project.status === "COMPLETED";

  if (!writable) {
    return {
      canRunPhase: false,
      canQueuePhase: false,
      canRunPackage: false,
      canRunFullCycle: false,
      canDecide: false,
      hint: "You have view access only on this project.",
    };
  }

  if (completed) {
    return {
      canRunPhase: false,
      canQueuePhase: false,
      canRunPackage: false,
      canRunFullCycle: false,
      canDecide: false,
      hint: "This project has completed the workflow. Review outputs or start a new project.",
    };
  }

  if (gatePending) {
    return {
      canRunPhase: false,
      canQueuePhase: false,
      canRunPackage: false,
      canRunFullCycle: false,
      canDecide: true,
      hint: "Review the outputs and either approve or reject the current decision gate.",
    };
  }

  if (atStart) {
    return {
      canRunPhase: true,
      canQueuePhase: true,
      canRunPackage: true,
      canRunFullCycle: true,
      canDecide: false,
      hint: "Start with a single phase or use V1 Package for the fastest end-to-end alpha test.",
    };
  }

  return {
    canRunPhase: true,
    canQueuePhase: true,
    canRunPackage: false,
    canRunFullCycle: false,
    canDecide: false,
    hint: "Run the current phase, then decide at the next gate.",
  };
}

function renderAuth() {
  const loggedIn = Boolean(state.user);
  const registrationOpen = state.access ? state.access.open_registration : true;
  const demoEnabled = Boolean(state.access && state.access.demo_account_enabled);
  document.getElementById("auth-status").textContent = loggedIn
    ? `Logged in as ${state.user.email} (${state.user.role})`
    : "Not logged in.";
  document.getElementById("access-copy").textContent = demoEnabled
    ? `Use the demo account ${state.access.demo_account_email} / ${state.access.demo_account_password}, or use credentials provided by the GhostStrike team.`
    : "Use the email and password provided by the GhostStrike team. Public signup may be disabled for alpha users.";
  document.getElementById("demo-login-button").classList.toggle("hidden", !demoEnabled);
  document.getElementById("logout-button").classList.toggle("hidden", !loggedIn);
  document.getElementById("create-form").classList.toggle("hidden", !loggedIn);
  document.getElementById("create-locked").classList.toggle("hidden", loggedIn);
  document.getElementById("accept-invitation-form").classList.toggle("hidden", !loggedIn);
  document.getElementById("register-form").classList.toggle("hidden", !registrationOpen);
  document.getElementById("admin-panel").classList.toggle("hidden", !loggedIn || state.user.role !== "ADMIN");
}

function renderProjects() {
  const container = document.getElementById("project-list");
  const summary = document.getElementById("project-summary");
  if (!state.user) {
    container.innerHTML = '<div class="empty-state compact-empty">Log in to view your projects.</div>';
    summary.textContent = "";
    return;
  }
  const filteredProjects = state.projects
    .filter((project) => {
      const search = state.projectSearch.trim().toLowerCase();
      if (search && !`${project.name} ${project.brief} ${project.owner_email || ""}`.toLowerCase().includes(search)) {
        return false;
      }
      switch (state.projectFilter) {
        case "NEEDS_REVIEW":
          return project.gate.status === "PENDING";
        case "ACTIVE":
          return project.status !== "COMPLETED" && project.gate.status !== "PENDING";
        case "OWNED":
          return project.owner_user_id === state.user.user_id;
        case "SHARED":
          return project.owner_user_id !== state.user.user_id;
        case "COMPLETED":
          return project.status === "COMPLETED";
        default:
          return true;
      }
    })
    .sort((left, right) => {
      const leftScore = left.gate.status === "PENDING" ? 0 : left.status === "COMPLETED" ? 2 : 1;
      const rightScore = right.gate.status === "PENDING" ? 0 : right.status === "COMPLETED" ? 2 : 1;
      if (leftScore !== rightScore) return leftScore - rightScore;
      return String(right.updated_at || "").localeCompare(String(left.updated_at || ""));
    });
  summary.textContent = `${filteredProjects.length} of ${state.projects.length} projects shown`;
  if (!filteredProjects.length) {
    container.innerHTML = '<div class="empty-state compact-empty">No projects yet. Create one or accept an invitation token.</div>';
    return;
  }
  container.innerHTML = filteredProjects
    .map((project) => {
      const sharedLabel = project.owner_user_id === state.user.user_id ? "Owned" : `Shared by ${escapeHtml(project.owner_email || "owner")}`;
      const priority = projectPriority(project);
      return `<article class="project-item ${project.project_id === state.selectedProjectId ? "active" : ""}" data-project-id="${project.project_id}">
        <h3>${escapeHtml(project.name)}</h3>
        <div class="project-meta">
          <span class="project-state-pill ${priority.className}">${escapeHtml(priority.label)}</span>
          <span class="project-state-pill">${escapeHtml(project.current_phase)}</span>
        </div>
        <p class="small">${escapeHtml(project.status)} · ${sharedLabel}</p>
        <p>${escapeHtml(project.brief.slice(0, 140))}${project.brief.length > 140 ? "..." : ""}</p>
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
    ? outputs
        .map((output) => `<article class="card output-card">
          <div class="output-header">
            <div>
              <h4>${escapeHtml(output.data.agent.display_name)}</h4>
              <p class="small">${escapeHtml(output.output_type)}</p>
            </div>
            <div class="output-meta">
              <span class="pill">v${escapeHtml(output.version)}</span>
              <span class="pill">${escapeHtml(output.sources?.length || 0)} sources</span>
            </div>
          </div>
          <div>
            <p class="small">Confidence ${escapeHtml(output.confidence_score)}</p>
            <div class="confidence-track"><div class="confidence-fill" style="width:${Math.round(Number(output.confidence_score || 0) * 100)}%"></div></div>
          </div>
          <p>${escapeHtml(output.data.summary || "No summary available.")}</p>
          <p class="small">Recommended questions: ${escapeHtml((output.data.recommended_questions || []).join(" | ") || "None")}</p>
        </article>`)
        .join("")
    : '<div class="empty-state compact-empty">No outputs yet. Run the current phase to produce output.</div>';
}

function renderMessages(runs, messages) {
  const container = document.getElementById("messages");
  const cards = [
    ...byNewest(runs || [], "created_at").map(
      (run) => `<article class="card">
        <div class="pill">${escapeHtml(run.status)}</div>
        <p><strong>${escapeHtml(run.phase)}</strong> · ${escapeHtml(run.summary)}</p>
        <p class="small">${escapeHtml(run.triggered_by)} · ${escapeHtml(run.created_at)}</p>
      </article>`,
    ),
    ...byNewest(messages || [], "timestamp").map(
      (message) => `<article class="card">
        <div class="pill">${escapeHtml(message.message_type)}</div>
        <p><strong>${escapeHtml(message.sender)}</strong> to <strong>${escapeHtml(message.receiver)}</strong></p>
        <p class="small">${escapeHtml(message.step)} · ${escapeHtml(message.phase)}</p>
      </article>`,
    ),
  ];
  container.innerHTML = cards.join("") || '<div class="empty-state compact-empty">No messages yet.</div>';
}

function renderCollaborators(snapshot) {
  const collaborators = snapshot.collaborators || [];
  document.getElementById("collaborator-list").innerHTML = collaborators.length
    ? collaborators
        .map((collaborator) => `<article class="card">
          <p><strong>${escapeHtml(collaborator.email || collaborator.user_id)}</strong></p>
          <p class="small">${escapeHtml(collaborator.access_role)}${collaborator.user_id === state.user?.user_id ? " · You" : ""}</p>
        </article>`)
        .join("")
    : '<div class="empty-state compact-empty">No collaborators yet.</div>';

  document.getElementById("invitation-list").innerHTML = state.invitations.length
    ? state.invitations
        .map((invitation) => `<article class="card">
          <p><strong>${escapeHtml(invitation.invited_email)}</strong></p>
          <p class="small">${escapeHtml(invitation.access_role)} · ${escapeHtml(invitation.status)}</p>
          <p class="small">Token: ${escapeHtml(invitation.token)}</p>
          <button type="button" class="ghost copy-token-button" data-token="${escapeHtml(invitation.token)}">Copy Token</button>
        </article>`)
        .join("")
    : '<div class="empty-state compact-empty">No invitations yet.</div>';

  document.getElementById("invite-form").classList.toggle("hidden", !isOwner(snapshot));
  document.querySelectorAll(".copy-token-button").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(button.dataset.token || "");
        showNotice("Invitation token copied.", "success");
      } catch (_error) {
        showNotice("Could not copy the token automatically. Copy it manually from the card.", "error");
      }
    });
  });
}

function renderFeedback(snapshot) {
  const feedback = byNewest(snapshot.feedback || [], "timestamp");
  document.getElementById("feedback-list").innerHTML = feedback.length
    ? feedback
        .map((item) => `<article class="card">
          <div class="pill">${escapeHtml(item.data.category || "GENERAL")}</div>
          <p>${escapeHtml(item.message)}</p>
          <p class="small">${escapeHtml(item.data.actor || "system")} · ${escapeHtml(item.timestamp)}</p>
        </article>`)
        .join("")
    : '<div class="empty-state compact-empty">No alpha feedback yet.</div>';
}

function renderOperations(snapshot) {
  const jobs = byNewest(snapshot.jobs || [], "created_at");
  const events = byNewest(snapshot.events || [], "timestamp").slice(0, 20);

  document.getElementById("jobs").innerHTML = jobs.length
    ? jobs
        .map((job) => `<article class="card">
          <div class="pill">${escapeHtml(job.status)}</div>
          <p><strong>${escapeHtml(job.phase)}</strong> · ${escapeHtml(job.job_type)}</p>
          <p class="small">${escapeHtml(job.requested_by)} · ${escapeHtml(job.created_at)}</p>
          ${job.error ? `<p class="small">${escapeHtml(job.error)}</p>` : ""}
        </article>`)
        .join("")
    : '<div class="empty-state compact-empty">No queued jobs yet.</div>';

  document.getElementById("events").innerHTML = events.length
    ? events
        .map((event) => `<article class="card">
          <div class="pill">${escapeHtml(event.level)}</div>
          <p><strong>${escapeHtml(event.event_type)}</strong></p>
          <p>${escapeHtml(event.message)}</p>
          <p class="small">${escapeHtml(event.data.actor || "system")} · ${escapeHtml(event.timestamp)}</p>
        </article>`)
        .join("")
    : '<div class="empty-state compact-empty">No events yet.</div>';
}

function renderPhaseRail(project) {
  const currentIndex = PHASES.indexOf(project.current_phase);
  const completed = project.status === "COMPLETED" ? currentIndex : currentIndex - 1;
  document.getElementById("phase-rail").innerHTML = PHASES.map((phase, index) => {
    const stateClass = index < completed ? "complete" : index === currentIndex ? "current" : "upcoming";
    return `<article class="phase-step ${stateClass}">
      <span class="phase-index">${index + 1}</span>
      <h4>${escapeHtml(phase)}</h4>
      <p class="small">${index < completed ? "Completed" : index === currentIndex ? "Active" : "Upcoming"}</p>
    </article>`;
  }).join("");
}

function renderProjectInsights(snapshot) {
  const { project, outputs, runs, feedback } = snapshot;
  const latestRun = (runs || [])[runs.length - 1];
  const nextStep = actionState(snapshot).hint;
  const insightCards = [
    {
      label: "Your Role",
      value: isOwner(snapshot) ? "Owner" : canWrite(snapshot) ? "Editor" : "Viewer",
    },
    {
      label: "Outputs Generated",
      value: String((outputs || []).length),
    },
    {
      label: "Latest Run",
      value: latestRun ? `${latestRun.phase} by ${latestRun.triggered_by}` : "No runs yet",
    },
    {
      label: "Next Step",
      value: nextStep,
    },
    {
      label: "Feedback Count",
      value: String((feedback || []).length),
    },
    {
      label: "Project Status",
      value: `${project.status} / Gate ${project.gate.status}`,
    },
  ];
  document.getElementById("project-insights").innerHTML = insightCards
    .map((item) => `<article class="insight-card">
      <span class="label">${escapeHtml(item.label)}</span>
      <strong>${escapeHtml(item.value)}</strong>
    </article>`)
    .join("");
}

function renderProjectDetail() {
  const emptyState = document.getElementById("empty-state");
  const detail = document.getElementById("project-detail");

  if (!state.user || !state.selectedSnapshot) {
    emptyState.classList.remove("hidden");
    renderWorkspaceEmptyState();
    detail.classList.add("hidden");
    return;
  }

  const snapshot = state.selectedSnapshot;
  const { project, outputs, messages, runs } = snapshot;
  const actions = actionState(snapshot);

  emptyState.classList.add("hidden");
  detail.classList.remove("hidden");

  document.getElementById("detail-name").textContent = project.name;
  document.getElementById("detail-subtitle").textContent = project.owner_user_id === state.user.user_id
    ? "You own this project."
    : `Shared with you by ${ownerLabel(project)}.`;
  document.getElementById("detail-phase").textContent = project.current_phase;
  document.getElementById("detail-status").textContent = project.status;
  document.getElementById("detail-gate").textContent = project.gate.status;
  document.getElementById("detail-owner").textContent = ownerLabel(project);
  document.getElementById("detail-brief").textContent = project.brief;
  document.getElementById("detail-phase-badge").textContent = project.current_phase;
  document.getElementById("detail-status-badge").textContent = project.status;
  document.getElementById("detail-gate-badge").textContent = `Gate ${project.gate.status}`;
  document.getElementById("action-hint").innerHTML = `<div class="workflow-callout"><strong>Recommended Next Move</strong><span>${escapeHtml(actions.hint)}</span></div>`;
  renderPhaseRail(project);
  renderProjectInsights(snapshot);

  document.getElementById("run-phase-button").disabled = !actions.canRunPhase;
  document.getElementById("queue-phase-button").disabled = !actions.canQueuePhase;
  document.getElementById("run-v1-button").disabled = !actions.canRunPackage;
  document.getElementById("run-full-cycle-button").disabled = !actions.canRunFullCycle;
  document.getElementById("approve-button").disabled = !actions.canDecide;
  document.getElementById("reject-button").disabled = !actions.canDecide;
  document.getElementById("decision-feedback").disabled = !actions.canDecide;

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
  const dashboard = state.adminDashboard;
  document.getElementById("admin-dashboard").innerHTML = dashboard
    ? [
        `<article class="metric-card"><span class="label">Build</span><strong>${escapeHtml(dashboard.build_label || "Unknown")}</strong></article>`,
        `<article class="metric-card"><span class="label">Users</span><strong>${escapeHtml(dashboard.user_count)}</strong></article>`,
        `<article class="metric-card"><span class="label">Projects</span><strong>${escapeHtml(dashboard.project_count)}</strong></article>`,
        `<article class="metric-card"><span class="label">Active Gates</span><strong>${escapeHtml(dashboard.active_gates)}</strong></article>`,
        `<article class="metric-card"><span class="label">Completed Projects</span><strong>${escapeHtml(dashboard.completed_projects)}</strong></article>`,
        `<article class="metric-card"><span class="label">Queued Jobs</span><strong>${escapeHtml(dashboard.queued_jobs)}</strong></article>`,
        `<article class="metric-card"><span class="label">Completed Jobs</span><strong>${escapeHtml(dashboard.completed_jobs)}</strong></article>`,
        `<article class="metric-card"><span class="label">Feedback Entries</span><strong>${escapeHtml(dashboard.feedback_count)}</strong></article>`,
        `<article class="metric-card"><span class="label">Feedback Mix</span><strong>${escapeHtml(Object.entries(dashboard.feedback_by_category || {}).map(([key, value]) => `${key}: ${value}`).join(" | ") || "None")}</strong></article>`,
        `<section class="activity-feed"><h3>Latest Activity</h3><div class="card-stack compact">${
          (dashboard.latest_activity || []).map((item) => `<article class="card">
            <div class="pill">${escapeHtml(item.event_type)}</div>
            <p>${escapeHtml(item.message)}</p>
            <p class="small">${escapeHtml(item.actor)} · ${escapeHtml(item.timestamp)}</p>
          </article>`).join("") || '<div class="empty-state compact-empty">No activity yet.</div>'
        }</div></section>`,
      ].join("")
    : "";
  document.getElementById("admin-users").innerHTML = state.adminUsers.length
    ? state.adminUsers
        .map((user) => `<article class="card">
          <p><strong>${escapeHtml(user.email)}</strong></p>
          <p class="small">${escapeHtml(user.role)}</p>
        </article>`)
        .join("")
    : '<div class="empty-state compact-empty">No users found.</div>';

  document.getElementById("admin-projects").innerHTML = state.adminProjects.length
    ? state.adminProjects
        .map((project) => `<article class="card">
          <p><strong>${escapeHtml(project.name)}</strong></p>
          <p class="small">${escapeHtml(project.owner_email || project.owner_user_id)} · ${escapeHtml(project.current_phase)} · ${escapeHtml(project.status)}</p>
        </article>`)
        .join("")
    : '<div class="empty-state compact-empty">No projects found.</div>';
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
    state.adminDashboard = null;
    state.adminUsers = [];
    state.adminProjects = [];
    return;
  }
  [state.adminDashboard, state.adminUsers, state.adminProjects] = await Promise.all([api("/admin/dashboard"), api("/admin/users"), api("/admin/projects")]);
  renderAdminPanel();
}

async function loadMetadata() {
  [state.agents, state.architecture, state.access] = await Promise.all([api("/meta/agents"), api("/meta/architecture"), api("/meta/access")]);
  document.getElementById("build-label").textContent = state.access?.build_label || "GhostStrike Alpha";
  document.getElementById("topbar-build-label").textContent = state.access?.build_label || "GhostStrike Alpha";
  document.getElementById("footer-build-label").textContent = state.access?.build_label || "GhostStrike Alpha";
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
  showNotice(`Logged in as ${response.user.email}.`, "success");
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
  showNotice(`Created project ${snapshot.project.name}.`, "success");
}

async function createSampleProjectFromTemplate() {
  if (!state.user) {
    showNotice("Log in before creating the sample project.", "info");
    return;
  }
  const snapshot = await api("/projects", {
    method: "POST",
    body: JSON.stringify(SAMPLE_BRIEF),
  });
  await Promise.all([loadProjects(), loadAdminData()]);
  state.selectedProjectId = snapshot.project.project_id;
  state.selectedSnapshot = snapshot;
  await loadProjectSharing(snapshot.project.project_id);
  renderProjects();
  renderProjectDetail();
  showNotice(`Created sample project ${snapshot.project.name}.`, "success");
}

async function runCurrentPhase() {
  if (!state.selectedProjectId) return;
  state.selectedSnapshot = await api(`/projects/${state.selectedProjectId}/start`, { method: "POST" });
  await Promise.all([loadProjects(), loadAdminData()]);
  await loadProjectSharing(state.selectedProjectId);
  renderProjectDetail();
  showNotice(`Ran ${state.selectedSnapshot.project.current_phase} and opened a review gate.`, "success");
}

async function queueCurrentPhase() {
  if (!state.selectedProjectId) return;
  const job = await api(`/projects/${state.selectedProjectId}/queue`, { method: "POST" });
  await refreshSelectedProject();
  showNotice(`Queued ${job.phase} as job ${job.job_id}. The worker will process it in the background.`, "info");
}

async function runV1Package() {
  if (!state.selectedProjectId) return;
  const result = await api(`/projects/${state.selectedProjectId}/flows/v1-package`, {
    method: "POST",
    body: JSON.stringify({ approval_feedback: "Proceed" }),
  });
  await refreshSelectedProject();
  await Promise.all([loadProjects(), loadAdminData()]);
  showNotice(`V1 Package completed with ${result.included_outputs.length} outputs.`, "success");
}

async function runFullCycle() {
  if (!state.selectedProjectId) return;
  const result = await api(`/projects/${state.selectedProjectId}/flows/full-cycle`, {
    method: "POST",
    body: JSON.stringify({ approval_feedback: "Proceed" }),
  });
  await refreshSelectedProject();
  await Promise.all([loadProjects(), loadAdminData()]);
  showNotice(`Full cycle completed with ${result.included_outputs.length} outputs.`, "success");
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
  showNotice(approved ? "Gate approved and project advanced." : "Gate rejected and project stopped for revision.", approved ? "success" : "info");
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
  showNotice("Invitation created.", "success");
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
  showNotice("Invitation accepted. The shared project is now in your project list.", "success");
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
  showNotice("Alpha user created.", "success");
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
  showNotice("Feedback submitted.", "success");
}

function fillSampleBrief() {
  document.getElementById("project-name").value = SAMPLE_BRIEF.name;
  document.getElementById("project-brief").value = SAMPLE_BRIEF.brief;
  showNotice("Loaded the sample alpha brief into the project form.", "info");
}

function fillDemoLogin() {
  if (!state.access || !state.access.demo_account_enabled) return;
  document.getElementById("login-email").value = state.access.demo_account_email;
  document.getElementById("login-password").value = state.access.demo_account_password;
  showNotice("Loaded the demo account into the login form.", "info");
}

function bindEvents() {
  document.getElementById("login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await submitAuth("/auth/login", document.getElementById("login-email").value, document.getElementById("login-password").value);
    } catch (error) {
      showNotice(error.message, "error");
    }
  });

  document.getElementById("register-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await submitAuth("/auth/register", document.getElementById("register-email").value, document.getElementById("register-password").value);
    } catch (error) {
      showNotice(error.message, "error");
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
    showNotice("Logged out.", "info");
  });

  document.getElementById("sample-brief-button").addEventListener("click", fillSampleBrief);
  document.getElementById("create-sample-project-button").addEventListener("click", async () => {
    try {
      await createSampleProjectFromTemplate();
    } catch (error) {
      showNotice(error.message, "error");
    }
  });
  document.getElementById("demo-login-button").addEventListener("click", fillDemoLogin);
  document.getElementById("project-search").addEventListener("input", (event) => {
    state.projectSearch = event.target.value;
    renderProjects();
  });
  document.getElementById("project-filter").addEventListener("change", (event) => {
    state.projectFilter = event.target.value;
    renderProjects();
  });

  document.getElementById("create-form").addEventListener("submit", async (event) => {
    try {
      await createProject(event);
    } catch (error) {
      showNotice(error.message, "error");
    }
  });

  document.getElementById("admin-create-user-form").addEventListener("submit", async (event) => {
    try {
      await createAdminUser(event);
    } catch (error) {
      showNotice(error.message, "error");
    }
  });

  document.getElementById("accept-invitation-form").addEventListener("submit", async (event) => {
    try {
      await acceptInvitation(event);
    } catch (error) {
      showNotice(error.message, "error");
    }
  });

  document.getElementById("invite-form").addEventListener("submit", async (event) => {
    try {
      await createInvitation(event);
    } catch (error) {
      showNotice(error.message, "error");
    }
  });

  document.getElementById("feedback-form").addEventListener("submit", async (event) => {
    try {
      await submitProjectFeedback(event);
    } catch (error) {
      showNotice(error.message, "error");
    }
  });

  document.getElementById("refresh-button").addEventListener("click", async () => {
    try {
      await refreshSelectedProject();
      showNotice("Project refreshed.", "info");
    } catch (error) {
      showNotice(error.message, "error");
    }
  });

  document.getElementById("run-phase-button").addEventListener("click", async () => {
    try {
      await runCurrentPhase();
    } catch (error) {
      showNotice(error.message, "error");
    }
  });

  document.getElementById("queue-phase-button").addEventListener("click", async () => {
    try {
      await queueCurrentPhase();
    } catch (error) {
      showNotice(error.message, "error");
    }
  });

  document.getElementById("run-v1-button").addEventListener("click", async () => {
    try {
      await runV1Package();
    } catch (error) {
      showNotice(error.message, "error");
    }
  });

  document.getElementById("run-full-cycle-button").addEventListener("click", async () => {
    try {
      await runFullCycle();
    } catch (error) {
      showNotice(error.message, "error");
    }
  });

  document.getElementById("approve-button").addEventListener("click", async () => {
    try {
      await submitDecision(true);
    } catch (error) {
      showNotice(error.message, "error");
    }
  });

  document.getElementById("reject-button").addEventListener("click", async () => {
    try {
      await submitDecision(false);
    } catch (error) {
      showNotice(error.message, "error");
    }
  });
}

async function boot() {
  bindEvents();
  await Promise.all([loadMetadata(), loadCurrentUser()]);
  await Promise.all([loadProjects(), loadAdminData()]);
  renderProjectDetail();
}

boot().catch((error) => showNotice(error.message, "error"));
