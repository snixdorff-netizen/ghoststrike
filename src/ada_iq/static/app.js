const SAMPLE_BRIEF = {
  name: "Trail Running Smart Brief Demo",
  smart_brief: {
    category: "Trail running footwear",
    price_point: "$165 premium performance",
    consumer_profile: "Experienced trail runners who want lightweight grip, underfoot protection, and all-day comfort for technical terrain and mixed-distance training.",
    geo_market: "United States specialty run and DTC launch",
    competitive_set: ["Hoka Speedgoat", "Nike Zegama", "Salomon Genesis"],
    brand_guardrails: "Must feel premium, performance-credible, and visually distinct without drifting into ultra-technical intimidation.",
    constraints: "Need launch-ready concept framing within one planning cycle and must stay inside premium-margin targets.",
    launch_season: "Spring 2027",
    uploaded_docs: ["trail_category_review.pdf", "consumer_signal_summary.docx"],
    open_context: "Use this as the seed Product Intelligence Brief to validate the new intake flow, research prompts, and downstream recommendation quality.",
  },
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
  smartBriefExport: null,
  editingSmartBriefModule: null,
  projectSearch: "",
  projectFilter: "ALL",
  briefStep: 1,
  summaryEditOpen: false,
};

const PHASES = ["EMPATHIZE", "IDEATE", "EVALUATE", "REALIZE", "MEASURE"];

function parseList(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function collectSmartBriefForm() {
  return {
    category: document.getElementById("brief-category").value.trim(),
    price_point: document.getElementById("brief-price-point").value.trim(),
    consumer_profile: document.getElementById("brief-consumer-profile").value.trim(),
    geo_market: document.getElementById("brief-geo-market").value.trim(),
    competitive_set: parseList(document.getElementById("brief-competitive-set").value),
    brand_guardrails: document.getElementById("brief-brand-guardrails").value.trim(),
    constraints: document.getElementById("brief-constraints").value.trim(),
    launch_season: document.getElementById("brief-launch-season").value.trim(),
    uploaded_docs: parseList(document.getElementById("brief-uploaded-docs").value),
    open_context: document.getElementById("brief-open-context").value.trim(),
  };
}

function composeSmartBriefSummary(name, smartBrief) {
  const competitors = smartBrief.competitive_set.length ? smartBrief.competitive_set.join(", ") : "the incumbent competitive set";
  return `Build a smart product brief for ${name} in ${smartBrief.category} at ${smartBrief.price_point}. Target ${smartBrief.consumer_profile} in ${smartBrief.geo_market} against ${competitors}. Brand guardrails: ${smartBrief.brand_guardrails || "maintain premium category fit"}. Constraints: ${smartBrief.constraints || "none specified"}. Launch season: ${smartBrief.launch_season || "to be confirmed"}. Additional context: ${smartBrief.open_context || "none provided"}`;
}

function syncGeneratedBrief() {
  const name = document.getElementById("project-name").value.trim() || "this product";
  const summary = composeSmartBriefSummary(name, collectSmartBriefForm());
  document.getElementById("project-brief").value = summary;
  document.getElementById("summary-preview-text").textContent = summary;
}

function setBriefStep(step) {
  state.briefStep = Math.max(1, Math.min(3, step));
  document.querySelectorAll("[data-brief-step]").forEach((panel) => {
    panel.classList.toggle("hidden", Number(panel.dataset.briefStep) !== state.briefStep);
  });
  document.querySelectorAll("[data-brief-step-chip]").forEach((chip) => {
    chip.classList.toggle("active", Number(chip.dataset.briefStepChip) === state.briefStep);
  });
  document.getElementById("brief-prev-button").disabled = state.briefStep === 1;
  document.getElementById("brief-next-button").classList.toggle("hidden", state.briefStep === 3);
  document.getElementById("brief-submit-button").classList.toggle("hidden", state.briefStep !== 3);
}

function toggleSummaryEdit(forceOpen) {
  state.summaryEditOpen = typeof forceOpen === "boolean" ? forceOpen : !state.summaryEditOpen;
  document.getElementById("summary-edit-wrap").classList.toggle("hidden", !state.summaryEditOpen);
  document.getElementById("toggle-summary-edit").textContent = state.summaryEditOpen ? "Use Generated Summary" : "Edit Summary";
}

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

function activateSidebarTarget(targetId) {
  document.querySelectorAll("[data-nav-target]").forEach((node) => {
    node.classList.toggle("active", node.dataset.navTarget === targetId);
    if (node.classList.contains("nav-item")) {
      node.classList.toggle("nav-item-active", node.dataset.navTarget === targetId);
    }
  });
}

function navigateToSection(targetId) {
  const target = document.getElementById(targetId);
  if (!target) return;
  target.scrollIntoView({ behavior: "smooth", block: "start" });
  activateSidebarTarget(targetId);
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
      <h3>Enter the Ada IQ private preview.</h3>
      <p>Once inside, you can create a project, accept a shared invitation, or use the curated sample brief to test the full product flow.</p>
      <div class="starter-grid">
        <article class="starter-card">
          <strong>1. Access</strong>
          <p>Use private credentials or the preview-entry flow if it is enabled for this site.</p>
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
      hint: "Generate Brief Insights first. That creates the initial Product Intelligence Brief package and opens the first review gate.",
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

function isInitialBriefExperience(snapshot) {
  if (!snapshot) return false;
  const { project } = snapshot;
  return project.current_phase === "EMPATHIZE" && (project.status === "DRAFT" || project.gate.status === "PENDING");
}

function renderQuickstartPanel(snapshot) {
  const panel = document.getElementById("quickstart-panel");
  const title = document.getElementById("quickstart-title");
  const description = document.getElementById("quickstart-description");
  const steps = document.getElementById("quickstart-steps");

  if (!snapshot || !isInitialBriefExperience(snapshot)) {
    panel.classList.add("hidden");
    steps.innerHTML = "";
    return;
  }

  const gatePending = snapshot.project.gate.status === "PENDING";
  title.textContent = gatePending ? "Review your first brief insights" : "Generate your first brief insights";
  description.textContent = gatePending
    ? "Ada IQ has already generated the first intelligence package from your Product Intelligence Brief. Review the outputs below, confirm the brief framing, then either advance or revise."
    : "Your Product Intelligence Brief is ready. Generate the first intelligence package to turn it into a decision-ready starting point.";

  const checklist = gatePending
    ? [
        { title: "1. Scan the outputs", detail: "Start with Ada Scout and Ada Empath to check whether the brief is pointed at the right market and customer." },
        { title: "2. Confirm the brief framing", detail: "Use the Product Intelligence Brief modules to check that the summary, constraints, and strategic direction match your intent." },
        { title: "3. Advance or revise", detail: "Approve to move forward, or revise the brief if the first pass is off target." },
      ]
    : [
        { title: "1. Generate the first pass", detail: "Run the opening EMPATHIZE step to create market and consumer intelligence from the brief." },
        { title: "2. Review the package", detail: "Read the outputs and modules before moving into the broader workflow." },
        { title: "3. Continue with confidence", detail: "Move into the next package only once the brief foundation looks strong." },
      ];

  steps.innerHTML = checklist.map((item) => `<article class="quickstart-step">
      <strong>${escapeHtml(item.title)}</strong>
      <p>${escapeHtml(item.detail)}</p>
    </article>`).join("");
  panel.classList.remove("hidden");
}

function renderAuth() {
  const loggedIn = Boolean(state.user);
  const registrationOpen = state.access ? state.access.open_registration : true;
  const demoEnabled = Boolean(state.access && state.access.demo_account_enabled);
  const publicDemoEnabled = Boolean(state.access && state.access.public_demo_access_enabled);
  document.documentElement.classList.toggle("has-token", loggedIn || Boolean(state.token));
  document.body.classList.toggle("logged-in", loggedIn);
  document.getElementById("auth-status").textContent = loggedIn
    ? `Logged in as ${state.user.email} (${state.user.role})`
    : "Not logged in.";
  document.getElementById("access-copy").textContent = publicDemoEnabled
    ? "Enter the private preview workspace instantly, or use your team credentials for a private account."
    : demoEnabled
      ? `Use the preview account ${state.access.demo_account_email} / ${state.access.demo_account_password}, or use credentials provided by the Ada IQ team.`
      : "Use the email and password provided by the Ada IQ team. Public signup may be disabled for this preview.";
  document.getElementById("demo-login-button").textContent = publicDemoEnabled ? "Enter Demo Workspace" : "Use Demo Login";
  document.getElementById("demo-login-button").classList.toggle("hidden", !demoEnabled);
  document.getElementById("hero-demo-button").classList.toggle("hidden", !publicDemoEnabled);
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

function renderDashboardStats() {
  const container = document.getElementById("dashboard-stats");
  const title = document.getElementById("dashboard-title");
  const subtitle = document.getElementById("dashboard-subtitle");

  if (!state.user) {
    title.textContent = "Ada IQ Private Preview";
    subtitle.textContent = "Enter the workspace to explore projects, outputs, and AI-guided product decisions.";
    container.innerHTML = "";
    return;
  }

  const projects = state.projects || [];
  const activeProjects = projects.filter((project) => project.status !== "COMPLETED").length;
  const pendingReview = projects.filter((project) => project.gate.status === "PENDING").length;
  const completedProjects = projects.filter((project) => project.status === "COMPLETED").length;
  const sharedProjects = projects.filter((project) => project.owner_user_id !== state.user.user_id).length;

  if (state.selectedSnapshot) {
    title.textContent = state.selectedSnapshot.project.name;
    subtitle.textContent = "AI-prioritized by urgency, workflow state, and pending decisions.";
  } else {
    title.textContent = "Ada IQ Projects Dashboard";
    subtitle.textContent = "AI-prioritized by urgency and pending actions.";
  }

  const cards = [
    { label: "Active Projects", value: String(activeProjects), note: `${projects.length} total in workspace` },
    { label: "Needs Review", value: String(pendingReview), note: "Projects waiting on a gate decision" },
    { label: "Completed", value: String(completedProjects), note: "Projects that reached the end of the workflow" },
    { label: "Shared With You", value: String(sharedProjects), note: "Cross-functional collaboration in progress" },
  ];

  container.innerHTML = cards.map((card) => `<article class="stats-card">
      <span class="label">${escapeHtml(card.label)}</span>
      <strong>${escapeHtml(card.value)}</strong>
      <p>${escapeHtml(card.note)}</p>
    </article>`).join("");
}

function renderOutputs(outputs) {
  const container = document.getElementById("outputs");
  container.innerHTML = outputs.length
    ? outputs
        .map((output) => {
          const summary = output.data.summary || "No summary available.";
          const recommendation = output.data.recommended_next_action
            || (output.data.recommended_questions || [])[0]
            || "Review the output and decide whether to advance the project.";
          const confidence = Math.round(Number(output.confidence_score || 0) * 100);
          const sourceCount = output.sources?.length || 0;
          const highlights = output.data.source_highlights || [];
          const citations = output.data.citations || [];
          return `<article class="card output-card">
          <div class="output-header">
            <div>
              <h4>${escapeHtml(output.data.agent.display_name)}</h4>
              <p class="small">${escapeHtml(output.output_type)}</p>
            </div>
            <div class="output-meta">
              <span class="pill">v${escapeHtml(output.version)}</span>
              <span class="pill">${escapeHtml(sourceCount)} sources</span>
            </div>
          </div>
          <p class="output-summary">${escapeHtml(summary)}</p>
          <div>
            <p class="small">Confidence ${escapeHtml(confidence)}%</p>
            <div class="confidence-track"><div class="confidence-fill" style="width:${confidence}%"></div></div>
          </div>
          ${highlights.length ? `<p class="small"><strong>Evidence:</strong> ${escapeHtml(highlights.join(" | "))}</p>` : ""}
          <p class="output-next"><strong>Next:</strong> ${escapeHtml(recommendation)}</p>
          ${citations.length ? `<div class="source-list">${citations.map((citation) => `<article class="source-item">
              <strong>${escapeHtml(citation.title || "Source")}</strong>
              <p class="small">${escapeHtml(citation.publisher || "Research source")}</p>
              <p>${escapeHtml(citation.note || "")}</p>
              ${citation.url ? `<p class="small"><a href="${escapeHtml(citation.url)}" target="_blank" rel="noreferrer">View source</a></p>` : ""}
            </article>`).join("")}</div>` : ""}
        </article>`;
        })
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

function renderSmartBrief(snapshot) {
  const container = document.getElementById("smart-brief-modules");
  const compliance = document.getElementById("compliance-summary");
  const exportContainer = document.getElementById("smart-brief-export");
  const smartBrief = snapshot.project.smart_brief;

  if (!smartBrief) {
    container.innerHTML = '<div class="empty-state compact-empty">This project was created before the Product Intelligence Brief workflow.</div>';
  } else {
    container.innerHTML = (smartBrief.modules || [])
      .map((module) => `<article class="card">
        <h4>${escapeHtml(module.title)}</h4>
        <p>${escapeHtml(module.content)}</p>
        <p class="small">v${escapeHtml(module.version || 1)} · Updated by ${escapeHtml(module.updated_by || "system")} · Revisions ${escapeHtml((module.revisions || []).length)}</p>
        ${module.citations?.length ? `<p class="small">Citations: ${escapeHtml(module.citations.join(", "))}</p>` : ""}
        ${canWrite(snapshot) ? `<button type="button" class="ghost smart-brief-edit-button" data-module-key="${escapeHtml(module.key)}">Edit Module</button>` : ""}
      </article>`)
      .join("");
  }

  const complianceProfile = snapshot.project.compliance || {};
  compliance.innerHTML = `<strong>Tenant & Compliance</strong><span>${escapeHtml(snapshot.project.tenant_id || "preview")} · ${escapeHtml(complianceProfile.status || "TRACKED")} · ${escapeHtml(complianceProfile.data_classification || "CONFIDENTIAL")}</span>`;
  if (state.smartBriefExport?.smart_brief_export) {
    const exportPayload = state.smartBriefExport.smart_brief_export;
    exportContainer.classList.remove("hidden");
    exportContainer.innerHTML = `<article class="card smart-brief-export-card">
      <h4>Product Intelligence Brief Snapshot</h4>
      <p>${escapeHtml(exportPayload.summary || "")}</p>
      <p class="small">Modules: ${escapeHtml((exportPayload.modules || []).length)} · Tenant: ${escapeHtml(exportPayload.tenant_id || "preview")}</p>
    </article>`;
  } else {
    exportContainer.classList.add("hidden");
    exportContainer.innerHTML = "";
  }
  document.querySelectorAll(".smart-brief-edit-button").forEach((button) => {
    button.addEventListener("click", () => startSmartBriefEdit(button.dataset.moduleKey));
  });
}

function startSmartBriefEdit(moduleKey) {
  const smartBrief = state.selectedSnapshot?.project?.smart_brief;
  if (!smartBrief) return;
  const module = (smartBrief.modules || []).find((item) => item.key === moduleKey);
  if (!module) return;
  state.editingSmartBriefModule = module.key;
  document.getElementById("smart-brief-editor").classList.remove("hidden");
  document.getElementById("smart-brief-editor-title").textContent = `Edit ${module.title}`;
  document.getElementById("smart-brief-editor-content").value = module.content;
  const history = (module.revisions || [])
    .slice()
    .reverse()
    .slice(0, 3)
    .map((revision) => `v${revision.version} · ${revision.updated_by}`)
    .join(" | ");
  document.getElementById("smart-brief-editor-title").textContent = history
    ? `Edit ${module.title} (${history})`
    : `Edit ${module.title}`;
}

function cancelSmartBriefEdit() {
  state.editingSmartBriefModule = null;
  document.getElementById("smart-brief-editor").classList.add("hidden");
  document.getElementById("smart-brief-editor-content").value = "";
}

function renderProjectDetail() {
  const emptyState = document.getElementById("empty-state");
  const detail = document.getElementById("project-detail");

  if (!state.user || !state.selectedSnapshot) {
    emptyState.classList.remove("hidden");
    renderWorkspaceEmptyState();
    detail.classList.add("hidden");
    renderDashboardStats();
    return;
  }

  const snapshot = state.selectedSnapshot;
  const { project, outputs, messages, runs } = snapshot;
  const actions = actionState(snapshot);
  const initialExperience = isInitialBriefExperience(snapshot);

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
  renderQuickstartPanel(snapshot);
  renderPhaseRail(project);
  renderProjectInsights(snapshot);
  renderSmartBrief(snapshot);
  document.getElementById("run-phase-button").textContent =
    project.current_phase === "EMPATHIZE" && project.status === "DRAFT"
      ? "Generate Brief Insights"
      : "Run Current Phase";
  document.getElementById("approve-button").textContent = initialExperience ? "Approve Brief Insights" : "Approve Gate";
  document.getElementById("reject-button").textContent = initialExperience ? "Revise Brief" : "Reject Gate";
  document.getElementById("run-v1-button").textContent = initialExperience ? "Continue to V1 Package" : "Run V1 Package";
  document.getElementById("advanced-actions").classList.toggle("hidden", initialExperience);

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
  renderDashboardStats();
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
    renderDashboardStats();
    return;
  }
  state.projects = await api("/projects");
  renderProjects();
  renderDashboardStats();
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
  document.getElementById("build-label").textContent = state.access?.build_label || "Ada IQ Private Preview";
  document.getElementById("topbar-build-label").textContent = state.access?.build_label || "Ada IQ Private Preview";
  document.getElementById("footer-build-label").textContent = state.access?.build_label || "Ada IQ Private Preview";
  renderMetadata();
  renderAuth();
  renderDashboardStats();
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

async function loadSmartBriefExport() {
  if (!state.selectedProjectId) return;
  state.smartBriefExport = await api(`/projects/${state.selectedProjectId}/smart-brief`);
  renderProjectDetail();
  showNotice("Loaded Product Intelligence Brief snapshot.", "success");
}

async function saveSmartBriefEdit() {
  if (!state.selectedProjectId || !state.editingSmartBriefModule) return;
  const packagePayload = await api(`/projects/${state.selectedProjectId}/smart-brief/modules/${state.editingSmartBriefModule}`, {
    method: "PATCH",
    body: JSON.stringify({ content: document.getElementById("smart-brief-editor-content").value }),
  });
  state.smartBriefExport = packagePayload;
  state.selectedSnapshot = await api(`/projects/${state.selectedProjectId}`);
  cancelSmartBriefEdit();
  renderProjectDetail();
  showNotice("Product Intelligence Brief module updated.", "success");
}

async function downloadSmartBriefExport() {
  if (!state.selectedProjectId) return;
  const packagePayload = await api(`/projects/${state.selectedProjectId}/smart-brief`);
  const blob = new Blob([JSON.stringify(packagePayload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${packagePayload.project_name || "product-intelligence-brief"}`.toLowerCase().replace(/[^a-z0-9]+/g, "-") + "-product-intelligence-brief.json";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  state.smartBriefExport = packagePayload;
  renderProjectDetail();
  showNotice("Downloaded Product Intelligence Brief package.", "success");
}

function openSmartBriefReport() {
  if (!state.selectedProjectId) return;
  window.open(`/projects/${state.selectedProjectId}/smart-brief/report`, "_blank", "noopener,noreferrer");
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
  const smartBrief = collectSmartBriefForm();
  const createdSnapshot = await api("/projects", {
    method: "POST",
    body: JSON.stringify({
      name: document.getElementById("project-name").value,
      brief: document.getElementById("project-brief").value,
      tenant_id: "preview",
      smart_brief: smartBrief,
    }),
  });
  document.getElementById("create-form").reset();
  setBriefStep(1);
  toggleSummaryEdit(false);
  syncGeneratedBrief();
  try {
    const snapshot = await api(`/projects/${createdSnapshot.project.project_id}/start`, { method: "POST" });
    await Promise.all([loadProjects(), loadAdminData()]);
    state.selectedProjectId = snapshot.project.project_id;
    state.selectedSnapshot = snapshot;
    await loadProjectSharing(snapshot.project.project_id);
    renderProjects();
    renderProjectDetail();
    showNotice(`Created ${snapshot.project.name}. Your first brief insights are ready for review.`, "success");
  } catch (error) {
    await Promise.all([loadProjects(), loadAdminData()]);
    state.selectedProjectId = createdSnapshot.project.project_id;
    state.selectedSnapshot = await api(`/projects/${createdSnapshot.project.project_id}`);
    await loadProjectSharing(createdSnapshot.project.project_id);
    renderProjects();
    renderProjectDetail();
    showNotice(`Created ${createdSnapshot.project.name}, but the first insight pass did not finish automatically. Open the project and click Generate Brief Insights. ${error.message}`, "error");
  }
}

async function createSampleProjectFromTemplate() {
  if (!state.user) {
    showNotice("Log in before creating the sample project.", "info");
    return;
  }
  const createdSnapshot = await api("/projects", {
    method: "POST",
    body: JSON.stringify({
      name: SAMPLE_BRIEF.name,
      brief: composeSmartBriefSummary(SAMPLE_BRIEF.name, SAMPLE_BRIEF.smart_brief),
      tenant_id: "preview",
      smart_brief: SAMPLE_BRIEF.smart_brief,
    }),
  });
  try {
    const snapshot = await api(`/projects/${createdSnapshot.project.project_id}/start`, { method: "POST" });
    await Promise.all([loadProjects(), loadAdminData()]);
    state.selectedProjectId = snapshot.project.project_id;
    state.selectedSnapshot = snapshot;
    await loadProjectSharing(snapshot.project.project_id);
    renderProjects();
    renderProjectDetail();
    showNotice(`Created sample project ${snapshot.project.name}. The first brief insights are already generated.`, "success");
  } catch (error) {
    await Promise.all([loadProjects(), loadAdminData()]);
    state.selectedProjectId = createdSnapshot.project.project_id;
    state.selectedSnapshot = await api(`/projects/${createdSnapshot.project.project_id}`);
    await loadProjectSharing(createdSnapshot.project.project_id);
    renderProjects();
    renderProjectDetail();
    showNotice(`Created sample project ${createdSnapshot.project.name}, but the first insight pass needs to be started manually. ${error.message}`, "error");
  }
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
  showNotice("Preview user created.", "success");
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
  document.getElementById("brief-category").value = SAMPLE_BRIEF.smart_brief.category;
  document.getElementById("brief-price-point").value = SAMPLE_BRIEF.smart_brief.price_point;
  document.getElementById("brief-consumer-profile").value = SAMPLE_BRIEF.smart_brief.consumer_profile;
  document.getElementById("brief-geo-market").value = SAMPLE_BRIEF.smart_brief.geo_market;
  document.getElementById("brief-competitive-set").value = SAMPLE_BRIEF.smart_brief.competitive_set.join(", ");
  document.getElementById("brief-brand-guardrails").value = SAMPLE_BRIEF.smart_brief.brand_guardrails;
  document.getElementById("brief-constraints").value = SAMPLE_BRIEF.smart_brief.constraints;
  document.getElementById("brief-launch-season").value = SAMPLE_BRIEF.smart_brief.launch_season;
  document.getElementById("brief-uploaded-docs").value = SAMPLE_BRIEF.smart_brief.uploaded_docs.join(", ");
  document.getElementById("brief-open-context").value = SAMPLE_BRIEF.smart_brief.open_context;
  syncGeneratedBrief();
  setBriefStep(3);
  showNotice("Loaded the sample Product Intelligence Brief into the project form.", "info");
}

function fillDemoLogin() {
  if (!state.access || !state.access.demo_account_enabled) return;
  if (state.access.public_demo_access_enabled) {
    demoAccess().catch((error) => showNotice(error.message, "error"));
    return;
  }
  document.getElementById("login-email").value = state.access.demo_account_email;
  document.getElementById("login-password").value = state.access.demo_account_password;
  showNotice("Loaded the demo account into the login form.", "info");
}

async function demoAccess() {
  const response = await api("/auth/demo", { method: "POST", body: JSON.stringify({}) });
  state.token = response.token;
  state.user = response.user;
  window.localStorage.setItem("ada_iq_token", state.token);
  renderAuth();
  await Promise.all([loadProjects(), loadAdminData()]);
  renderProjectDetail();
  showNotice("Entered the shared demo workspace.", "success");
}

function bindEvents() {
  document.querySelectorAll("[data-nav-target]").forEach((node) => {
    node.addEventListener("click", () => navigateToSection(node.dataset.navTarget));
  });

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
  renderDashboardStats();
  showNotice("Logged out.", "info");
  });

  document.getElementById("sample-brief-button").addEventListener("click", fillSampleBrief);
  document.getElementById("export-smart-brief-button").addEventListener("click", async () => {
    try {
      await loadSmartBriefExport();
    } catch (error) {
      showNotice(error.message, "error");
    }
  });
  document.getElementById("download-smart-brief-button").addEventListener("click", async () => {
    try {
      await downloadSmartBriefExport();
    } catch (error) {
      showNotice(error.message, "error");
    }
  });
  document.getElementById("open-smart-brief-report-button").addEventListener("click", openSmartBriefReport);
  document.getElementById("cancel-smart-brief-edit-button").addEventListener("click", cancelSmartBriefEdit);
  document.getElementById("save-smart-brief-edit-button").addEventListener("click", async () => {
    try {
      await saveSmartBriefEdit();
    } catch (error) {
      showNotice(error.message, "error");
    }
  });
  document.querySelectorAll("[data-brief-step-chip]").forEach((chip) => {
    chip.addEventListener("click", () => setBriefStep(Number(chip.dataset.briefStepChip)));
  });
  document.getElementById("brief-prev-button").addEventListener("click", () => setBriefStep(state.briefStep - 1));
  document.getElementById("brief-next-button").addEventListener("click", () => setBriefStep(state.briefStep + 1));
  document.getElementById("toggle-summary-edit").addEventListener("click", () => toggleSummaryEdit());
  document.getElementById("create-sample-project-button").addEventListener("click", async () => {
    try {
      await createSampleProjectFromTemplate();
    } catch (error) {
      showNotice(error.message, "error");
    }
  });
  document.getElementById("demo-login-button").addEventListener("click", fillDemoLogin);
  document.getElementById("hero-demo-button").addEventListener("click", async () => {
    try {
      await demoAccess();
    } catch (error) {
      showNotice(error.message, "error");
    }
  });
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
  [
    "project-name",
    "brief-category",
    "brief-price-point",
    "brief-consumer-profile",
    "brief-geo-market",
    "brief-competitive-set",
    "brief-brand-guardrails",
    "brief-constraints",
    "brief-launch-season",
    "brief-uploaded-docs",
    "brief-open-context",
  ].forEach((id) => {
    document.getElementById(id).addEventListener("input", syncGeneratedBrief);
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
  setBriefStep(1);
  toggleSummaryEdit(false);
  syncGeneratedBrief();
  await Promise.all([loadMetadata(), loadCurrentUser()]);
  await Promise.all([loadProjects(), loadAdminData()]);
  renderProjectDetail();
  renderDashboardStats();
}

boot().catch((error) => showNotice(error.message, "error"));
