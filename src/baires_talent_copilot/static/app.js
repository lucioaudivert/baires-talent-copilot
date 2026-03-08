const STORAGE_KEY = "baires_talent_copilot_token";

const state = {
  authToken: localStorage.getItem(STORAGE_KEY),
  authConfig: null,
  currentUser: null,
  roles: [],
  screenings: [],
  selectedScreeningId: null,
  selectedScreening: null,
  pipelineSearch: "",
  pipelineRoleFilter: "",
  pipelineStatusFilter: "all",
  draggingScreeningId: null,
};

const els = {};

document.addEventListener("DOMContentLoaded", async () => {
  bindElements();
  bindEvents();
  await initializeApp();
});

function bindElements() {
  els.authPanel = document.querySelector("#auth-panel");
  els.workspace = document.querySelector("#workspace");
  els.loginForm = document.querySelector("#login-form");
  els.registerForm = document.querySelector("#register-form");
  els.fillDemo = document.querySelector("#fill-demo");
  els.logoutButton = document.querySelector("#logout-button");
  els.statusLine = document.querySelector("#status-line");
  els.demoCard = document.querySelector("#demo-card");
  els.demoDisplayName = document.querySelector("#demo-display-name");
  els.demoEmail = document.querySelector("#demo-email");
  els.demoPassword = document.querySelector("#demo-password");
  els.accountName = document.querySelector("#account-name");
  els.accountEmail = document.querySelector("#account-email");

  els.roleForm = document.querySelector("#role-form");
  els.screeningForm = document.querySelector("#screening-form");
  els.messageForm = document.querySelector("#message-form");
  els.rolesCount = document.querySelector("#roles-count");
  els.screeningsCount = document.querySelector("#screenings-count");
  els.reviewReadyCount = document.querySelector("#review-ready-count");
  els.rolesList = document.querySelector("#roles-list");
  els.screeningsList = document.querySelector("#screenings-list");
  els.screeningRoleId = document.querySelector("#screening-role-id");
  els.pipelineSearch = document.querySelector("#pipeline-search");
  els.pipelineRoleFilter = document.querySelector("#pipeline-role-filter");
  els.pipelineStatusButtons = document.querySelectorAll("#pipeline-statuses .filter-chip");
  els.bootstrapDemo = document.querySelector("#bootstrap-demo");
  els.refreshData = document.querySelector("#refresh-data");
  els.runAnalysis = document.querySelector("#run-analysis");
  els.detailEmpty = document.querySelector("#detail-empty");
  els.detailContent = document.querySelector("#detail-content");
  els.detailCandidateName = document.querySelector("#detail-candidate-name");
  els.detailStatus = document.querySelector("#detail-status");
  els.detailRoleTitle = document.querySelector("#detail-role-title");
  els.detailRoleSummary = document.querySelector("#detail-role-summary");
  els.detailIntroNotes = document.querySelector("#detail-intro-notes");
  els.messagesList = document.querySelector("#messages-list");
  els.analysisSkills = document.querySelector("#analysis-skills");
  els.analysisMissing = document.querySelector("#analysis-missing");
  els.analysisSummary = document.querySelector("#analysis-summary");
  els.analysisConfidence = document.querySelector("#analysis-confidence");
  els.analysisSource = document.querySelector("#analysis-source");
  els.analysisStatus = document.querySelector("#analysis-status");
  els.analysisQuestions = document.querySelector("#analysis-questions");
  els.auditList = document.querySelector("#audit-list");
  els.messageContent = document.querySelector("#message-content");
  els.messageHint = document.querySelector("#message-hint");
}

function bindEvents() {
  els.loginForm.addEventListener("submit", onLoginSubmit);
  els.registerForm.addEventListener("submit", onRegisterSubmit);
  els.fillDemo.addEventListener("click", fillDemoCredentials);
  els.logoutButton.addEventListener("click", onLogoutClick);

  els.roleForm.addEventListener("submit", onRoleSubmit);
  els.screeningForm.addEventListener("submit", onScreeningSubmit);
  els.messageForm.addEventListener("submit", onMessageSubmit);
  els.bootstrapDemo.addEventListener("click", onBootstrapDemo);
  els.refreshData.addEventListener("click", () => loadBoard());
  els.runAnalysis.addEventListener("click", onRunAnalysis);
  els.pipelineSearch.addEventListener("input", onPipelineFiltersChange);
  els.pipelineRoleFilter.addEventListener("change", onPipelineFiltersChange);
  els.pipelineStatusButtons.forEach((button) => {
    button.addEventListener("click", () => onPipelineStatusClick(button.dataset.status));
  });
}

async function initializeApp() {
  await loadAuthConfig();
  renderAuthShell();

  if (state.authToken) {
    const restored = await restoreSession();
    if (restored) {
      await loadBoard();
      return;
    }
  }

  setStatus("Sign in with a recruiter account to access your private pipeline.");
}

async function loadAuthConfig() {
  try {
    state.authConfig = await api("/auth/config", { auth: false });
  } catch (error) {
    state.authConfig = null;
    setStatus(error.message, true);
  }
  renderDemoCard();
}

async function restoreSession() {
  try {
    state.currentUser = await api("/auth/me");
    renderAuthShell();
    return true;
  } catch (error) {
    clearSession(false);
    renderAuthShell();
    return false;
  }
}

function renderAuthShell() {
  const isAuthenticated = Boolean(state.currentUser);
  els.authPanel.classList.toggle("hidden", isAuthenticated);
  els.workspace.classList.toggle("hidden", !isAuthenticated);

  if (state.currentUser) {
    els.accountName.textContent = state.currentUser.display_name;
    els.accountEmail.textContent = state.currentUser.email;
  } else {
    resetWorkspaceState();
  }
}

function renderDemoCard() {
  if (!state.authConfig?.demo_account_enabled) {
    els.demoCard.classList.add("hidden");
    els.fillDemo.disabled = true;
    return;
  }

  els.fillDemo.disabled = false;
  els.demoCard.classList.remove("hidden");
  els.demoDisplayName.textContent = state.authConfig.demo_display_name;
  els.demoEmail.textContent = state.authConfig.demo_email;
  els.demoPassword.textContent = state.authConfig.demo_password;
}

function fillDemoCredentials() {
  if (!state.authConfig?.demo_account_enabled) {
    return;
  }

  document.querySelector("#login-email").value = state.authConfig.demo_email;
  document.querySelector("#login-password").value = state.authConfig.demo_password;
  setStatus("Demo credentials filled. Sign in to continue.");
}

async function onLoginSubmit(event) {
  event.preventDefault();
  setStatus("Signing in...");

  try {
    const session = await api("/auth/login", {
      auth: false,
      method: "POST",
      body: JSON.stringify({
        email: document.querySelector("#login-email").value.trim(),
        password: document.querySelector("#login-password").value,
      }),
    });
    storeSession(session);
    await loadBoard();
    setStatus(`Signed in as ${session.user.display_name}.`);
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function onRegisterSubmit(event) {
  event.preventDefault();
  setStatus("Creating recruiter account...");

  try {
    const session = await api("/auth/register", {
      auth: false,
      method: "POST",
      body: JSON.stringify({
        display_name: document.querySelector("#register-display-name").value.trim(),
        email: document.querySelector("#register-email").value.trim(),
        password: document.querySelector("#register-password").value,
      }),
    });
    storeSession(session);
    await loadBoard();
    setStatus(`Account created for ${session.user.display_name}.`);
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function onLogoutClick() {
  setStatus("Signing out...");

  try {
    await api("/auth/logout", { method: "POST" });
  } catch (error) {
    // Ignore server-side logout failures and clear local state anyway.
  }

  clearSession();
  setStatus("Signed out.");
}

function storeSession(sessionPayload) {
  state.authToken = sessionPayload.access_token;
  state.currentUser = sessionPayload.user;
  localStorage.setItem(STORAGE_KEY, state.authToken);
  els.loginForm.reset();
  els.registerForm.reset();
  renderAuthShell();
}

function clearSession(announce = true) {
  state.authToken = null;
  state.currentUser = null;
  localStorage.removeItem(STORAGE_KEY);
  state.draggingScreeningId = null;
  renderAuthShell();
  if (announce) {
    setStatus("Session cleared.");
  }
}

function resetWorkspaceState() {
  state.roles = [];
  state.screenings = [];
  state.selectedScreeningId = null;
  state.selectedScreening = null;
  state.pipelineSearch = "";
  state.pipelineRoleFilter = "";
  state.pipelineStatusFilter = "all";
  state.draggingScreeningId = null;
  els.rolesCount.textContent = "0";
  els.screeningsCount.textContent = "0";
  els.reviewReadyCount.textContent = "0";
  els.rolesList.innerHTML = "";
  els.screeningsList.innerHTML = "";
  els.pipelineSearch.value = "";
  els.pipelineRoleFilter.innerHTML = '<option value="">All roles</option>';
  updatePipelineStatusButtons();
  els.detailEmpty.classList.remove("hidden");
  els.detailContent.classList.add("hidden");
  els.auditList.innerHTML = "";
}

async function onRoleSubmit(event) {
  event.preventDefault();
  setStatus("Saving role profile...");

  const payload = {
    title: document.querySelector("#role-title").value.trim(),
    seniority: document.querySelector("#role-seniority").value.trim(),
    language: document.querySelector("#role-language").value.trim() || "es",
    summary: document.querySelector("#role-summary").value.trim(),
    must_have_skills: toList(document.querySelector("#role-must-have").value),
    nice_to_have_skills: toList(document.querySelector("#role-nice-to-have").value),
  };

  try {
    const role = await api("/roles", { method: "POST", body: JSON.stringify(payload) });
    els.roleForm.reset();
    document.querySelector("#role-language").value = "es";
    await loadBoard();
    document.querySelector("#screening-role-id").value = String(role.id);
    setStatus(`Role profile "${role.title}" saved.`);
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function onScreeningSubmit(event) {
  event.preventDefault();
  if (!state.roles.length) {
    setStatus("Create a role profile before opening a screening.", true);
    return;
  }

  setStatus("Creating screening...");

  const payload = {
    role_id: Number(document.querySelector("#screening-role-id").value),
    candidate_name: document.querySelector("#candidate-name").value.trim(),
    candidate_email: optionalValue(document.querySelector("#candidate-email").value),
    intro_notes: optionalValue(document.querySelector("#candidate-intro-notes").value),
  };

  try {
    const screening = await api("/screenings", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    els.screeningForm.reset();
    await loadBoard(screening.id);
    setStatus(`Screening opened for ${screening.candidate_name}.`);
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function onMessageSubmit(event) {
  event.preventDefault();
  if (!state.selectedScreeningId) {
    setStatus("Select a screening before adding messages.", true);
    return;
  }

  const hint = optionalValue(els.messageHint.value);
  const content = els.messageContent.value.trim();
  const finalContent = hint ? `${content}\n\nContext: ${hint}` : content;

  setStatus("Adding message...");

  try {
    await api(`/screenings/${state.selectedScreeningId}/messages`, {
      method: "POST",
      body: JSON.stringify({
        speaker: document.querySelector("#message-speaker").value,
        content: finalContent,
      }),
    });
    els.messageForm.reset();
    await selectScreening(state.selectedScreeningId);
    setStatus("Message added to timeline.");
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function onRunAnalysis() {
  if (!state.selectedScreeningId) {
    setStatus("Select a screening before generating analysis.", true);
    return;
  }

  setStatus("Generating analysis...");

  try {
    const analysis = await api(`/screenings/${state.selectedScreeningId}/analysis`, {
      method: "POST",
    });
    await loadBoard(state.selectedScreeningId);
    setStatus(`Analysis generated with ${analysis.analysis_source}.`);
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function onBootstrapDemo() {
  setStatus("Loading demo workflow...");

  try {
    const detail = await api("/demo/bootstrap", { method: "POST" });
    await loadBoard(detail.id);
    setStatus(`Demo workflow ready for ${detail.candidate_name}.`);
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function onPipelineFiltersChange() {
  state.pipelineSearch = els.pipelineSearch.value.trim();
  state.pipelineRoleFilter = els.pipelineRoleFilter.value;
  await syncSelectionWithBoard();
}

async function onPipelineStatusClick(status) {
  state.pipelineStatusFilter = status;
  updatePipelineStatusButtons();
  await syncSelectionWithBoard();
}

async function loadBoard(preferScreeningId = null) {
  if (!state.currentUser) {
    return;
  }

  try {
    const [roles, screenings] = await Promise.all([api("/roles"), api("/screenings")]);
    state.roles = roles;
    state.screenings = screenings;

    renderRoleOptions();
    renderRoleCards();
    renderStats();
    await syncSelectionWithBoard(preferScreeningId);
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function syncSelectionWithBoard(preferScreeningId = null) {
  const filteredScreenings = getFilteredScreenings();
  renderScreeningCards(filteredScreenings);

  const nextId = filteredScreenings.some((item) => item.id === preferScreeningId)
    ? preferScreeningId
    : filteredScreenings.some((item) => item.id === state.selectedScreeningId)
      ? state.selectedScreeningId
      : filteredScreenings[0]?.id ?? null;

  if (nextId) {
    await selectScreening(nextId);
    return;
  }

  state.selectedScreeningId = null;
  state.selectedScreening = null;
  renderDetail();
}

async function selectScreening(screeningId) {
  state.selectedScreeningId = screeningId;

  try {
    state.selectedScreening = await api(`/screenings/${screeningId}`);
    renderScreeningCards();
    renderDetail();
  } catch (error) {
    setStatus(error.message, true);
  }
}

function renderRoleOptions() {
  if (!state.roles.length) {
    els.screeningRoleId.innerHTML = '<option value="">Create a role first</option>';
    els.screeningRoleId.disabled = true;
    els.pipelineRoleFilter.innerHTML = '<option value="">All roles</option>';
    els.pipelineRoleFilter.disabled = true;
    return;
  }

  els.screeningRoleId.disabled = false;
  els.screeningRoleId.innerHTML = state.roles
    .map(
      (role) =>
        `<option value="${role.id}">${escapeHtml(role.title)} · ${escapeHtml(role.seniority)}</option>`,
    )
    .join("");
  els.pipelineRoleFilter.disabled = false;
  els.pipelineRoleFilter.innerHTML = [
    '<option value="">All roles</option>',
    ...state.roles.map(
      (role) =>
        `<option value="${role.id}">${escapeHtml(role.title)} · ${escapeHtml(role.seniority)}</option>`,
    ),
  ].join("");
  els.pipelineRoleFilter.value = state.pipelineRoleFilter;
}

function renderRoleCards() {
  if (!state.roles.length) {
    els.rolesList.innerHTML =
      '<div class="empty-state"><p>No role profiles yet. Start with a target role.</p></div>';
    return;
  }

  els.rolesList.innerHTML = state.roles
    .map(
      (role) => `
        <article class="list-card">
          <strong>${escapeHtml(role.title)}</strong>
          <p>${escapeHtml(role.summary)}</p>
          <div class="tag">${escapeHtml(role.seniority)} · ${escapeHtml(role.language)}</div>
        </article>
      `,
    )
    .join("");
}

function renderScreeningCards(filteredScreenings = getFilteredScreenings()) {
  if (!state.screenings.length) {
    els.screeningsList.innerHTML =
      '<div class="empty-state"><p>No screenings yet. Create one or load the demo.</p></div>';
    return;
  }

  if (!filteredScreenings.length) {
    els.screeningsList.innerHTML =
      '<div class="empty-state"><p>No screenings match the current filters.</p></div>';
    return;
  }

  const statuses = ["draft", "in_progress", "review_ready"];
  els.screeningsList.innerHTML = statuses
    .map((status) => renderBoardColumn(status, filteredScreenings))
    .join("");

  els.screeningsList.querySelectorAll(".screening-card").forEach((card) => {
    card.addEventListener("click", () => selectScreening(Number(card.dataset.screeningId)));
    card.addEventListener("dragstart", onScreeningDragStart);
    card.addEventListener("dragend", onScreeningDragEnd);
  });
  els.screeningsList.querySelectorAll(".board-column").forEach((column) => {
    column.addEventListener("dragover", onBoardColumnDragOver);
    column.addEventListener("dragleave", onBoardColumnDragLeave);
    column.addEventListener("drop", onBoardColumnDrop);
  });
}

function renderStats() {
  const reviewReady = state.screenings.filter((item) => item.status === "review_ready").length;
  els.rolesCount.textContent = String(state.roles.length);
  els.screeningsCount.textContent = String(state.screenings.length);
  els.reviewReadyCount.textContent = String(reviewReady);
}

function renderBoardColumn(status, screenings) {
  const items = screenings.filter((screening) => screening.status === status);
  const cards = items.length
    ? items.map((screening) => renderScreeningCard(screening)).join("")
    : `<div class="column-empty"><p>No ${escapeHtml(humanizeToken(status).toLowerCase())} screenings.</p></div>`;

  return `
    <section class="board-column" data-status="${status}">
      <div class="board-column-head">
        <div>
          <p class="eyebrow">${escapeHtml(humanizeToken(status))}</p>
          <h3>${items.length}</h3>
        </div>
        <span class="ghost-pill">${escapeHtml(statusSummaryLabel(status))}</span>
      </div>
      <div class="board-column-body">
        ${cards}
      </div>
    </section>
  `;
}

function renderScreeningCard(screening) {
  const selectedClass = screening.id === state.selectedScreeningId ? "selected" : "";
  const role = state.roles.find((item) => item.id === screening.role_id);
  const summary = screening.latest_summary
    ? `<p class="screening-summary">${escapeHtml(truncateText(screening.latest_summary, 120))}</p>`
    : '<p class="screening-summary muted">No AI summary yet.</p>';

  return `
    <article
      class="screening-card ${selectedClass}"
      data-screening-id="${screening.id}"
      data-status="${screening.status}"
      draggable="true"
    >
      <div class="screening-card-head">
        <strong>${escapeHtml(screening.candidate_name)}</strong>
        <span class="pill">${escapeHtml(humanizeToken(screening.status))}</span>
      </div>
      <p>${escapeHtml(role?.title || "Unknown role")}</p>
      <small>${escapeHtml(screening.candidate_email || "No email")} · ${screening.message_count} messages</small>
      ${summary}
      <div class="screening-card-meta">
        <span class="tag">${escapeHtml(formatDate(screening.updated_at))}</span>
      </div>
    </article>
  `;
}

function getFilteredScreenings() {
  const search = state.pipelineSearch.toLowerCase();
  const roleFilter = state.pipelineRoleFilter;
  const statusFilter = state.pipelineStatusFilter;

  return state.screenings.filter((screening) => {
    const role = state.roles.find((item) => item.id === screening.role_id);
    const matchesRole = !roleFilter || String(screening.role_id) === roleFilter;
    const matchesStatus = statusFilter === "all" || screening.status === statusFilter;
    const haystack = [
      screening.candidate_name,
      screening.candidate_email,
      screening.intro_notes,
      screening.latest_summary,
      role?.title,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    const matchesSearch = !search || haystack.includes(search);

    return matchesRole && matchesStatus && matchesSearch;
  });
}

function onScreeningDragStart(event) {
  const card = event.currentTarget;
  state.draggingScreeningId = Number(card.dataset.screeningId);
  card.classList.add("dragging");
  event.dataTransfer.effectAllowed = "move";
  event.dataTransfer.setData("text/plain", String(state.draggingScreeningId));
}

function onScreeningDragEnd(event) {
  event.currentTarget.classList.remove("dragging");
  clearBoardDropTargets();
  state.draggingScreeningId = null;
}

function onBoardColumnDragOver(event) {
  if (!state.draggingScreeningId) {
    return;
  }

  event.preventDefault();
  event.dataTransfer.dropEffect = "move";
  event.currentTarget.classList.add("drop-ready");
}

function onBoardColumnDragLeave(event) {
  if (event.currentTarget.contains(event.relatedTarget)) {
    return;
  }

  event.currentTarget.classList.remove("drop-ready");
}

async function onBoardColumnDrop(event) {
  event.preventDefault();
  const column = event.currentTarget;
  const screeningId = Number(event.dataTransfer.getData("text/plain") || state.draggingScreeningId);
  const nextStatus = column.dataset.status;
  clearBoardDropTargets();

  if (!screeningId || !nextStatus) {
    return;
  }

  const screening = state.screenings.find((item) => item.id === screeningId);
  if (!screening || screening.status === nextStatus) {
    return;
  }

  setStatus(`Moving ${screening.candidate_name} to ${humanizeToken(nextStatus)}...`);

  try {
    await api(`/screenings/${screeningId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status: nextStatus }),
    });
    await loadBoard(screeningId);
    setStatus(`Moved ${screening.candidate_name} to ${humanizeToken(nextStatus)}.`);
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    state.draggingScreeningId = null;
  }
}

function clearBoardDropTargets() {
  els.screeningsList.querySelectorAll(".board-column").forEach((column) => {
    column.classList.remove("drop-ready");
  });
}

function updatePipelineStatusButtons() {
  els.pipelineStatusButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.status === state.pipelineStatusFilter);
  });
}

function statusSummaryLabel(status) {
  if (status === "draft") {
    return "New";
  }
  if (status === "in_progress") {
    return "Active";
  }
  return "Ready";
}

function renderDetail() {
  const detail = state.selectedScreening;

  if (!detail) {
    els.detailEmpty.classList.remove("hidden");
    els.detailContent.classList.add("hidden");
    els.auditList.innerHTML = "";
    return;
  }

  els.detailEmpty.classList.add("hidden");
  els.detailContent.classList.remove("hidden");

  els.detailCandidateName.textContent = detail.candidate_name;
  els.detailStatus.textContent = detail.status;
  els.detailRoleTitle.textContent = detail.role.title;
  els.detailRoleSummary.textContent = detail.role.summary;
  els.detailIntroNotes.textContent = detail.intro_notes || "No intro notes recorded yet.";

  els.messagesList.innerHTML = detail.messages.length
    ? detail.messages
        .map(
          (message) => `
            <article class="message" data-speaker="${message.speaker}">
              <div class="message-head">
                <span>${escapeHtml(message.speaker)}</span>
                <span>${formatDate(message.created_at)}</span>
              </div>
              <p>${escapeHtml(message.content).replaceAll("\n", "<br />")}</p>
            </article>
          `,
        )
        .join("")
    : '<div class="empty-state"><p>No messages yet. Add the first screening exchange.</p></div>';

  renderAuditTrail(detail.audit_events || []);

  if (!detail.latest_analysis) {
    els.analysisSummary.textContent =
      "No analysis generated yet. Add candidate messages and run the analysis step.";
    els.analysisConfidence.textContent = "0.00";
    els.analysisSource.textContent = "pending";
    els.analysisStatus.textContent = detail.status;
    els.analysisQuestions.innerHTML = "<li>Generate analysis to populate follow-up questions.</li>";
    els.analysisSkills.innerHTML = '<span class="tag">No matched skills yet</span>';
    els.analysisMissing.innerHTML =
      '<span class="tag">Missing signals will appear here</span>';
    return;
  }

  const analysis = detail.latest_analysis;
  els.analysisSummary.textContent = analysis.summary;
  els.analysisConfidence.textContent = analysis.confidence_score.toFixed(2);
  els.analysisSource.textContent = analysis.analysis_source;
  els.analysisStatus.textContent = analysis.recommended_status;
  els.analysisQuestions.innerHTML = analysis.follow_up_questions
    .map((question) => `<li>${escapeHtml(question)}</li>`)
    .join("");
  els.analysisSkills.innerHTML = analysis.matched_skills.length
    ? analysis.matched_skills.map((skill) => `<span class="tag">${escapeHtml(skill)}</span>`).join("")
    : '<span class="tag">No matched skills yet</span>';
  els.analysisMissing.innerHTML = analysis.missing_signals.length
    ? analysis.missing_signals.map((skill) => `<span class="tag">${escapeHtml(skill)}</span>`).join("")
    : '<span class="tag">No missing signals</span>';
}

function renderAuditTrail(events) {
  if (!events.length) {
    els.auditList.innerHTML =
      '<div class="empty-state"><p>No audit events recorded yet.</p></div>';
    return;
  }

  els.auditList.innerHTML = events
    .map((event) => {
      const badges = buildAuditBadges(event.payload);
      return `
        <article class="audit-event" data-event-type="${event.event_type}">
          <div class="audit-head">
            <div>
              <strong>${escapeHtml(humanizeAuditEvent(event.event_type))}</strong>
              <p>${escapeHtml(event.summary)}</p>
            </div>
            <span class="audit-time">${formatDate(event.created_at)}</span>
          </div>
          <div class="audit-meta">
            <span class="tag">${escapeHtml(event.actor_label)}</span>
            <span class="ghost-pill">${escapeHtml(event.actor_type)}</span>
            ${badges}
          </div>
        </article>
      `;
    })
    .join("");
}

function buildAuditBadges(payload) {
  if (!payload) {
    return "";
  }

  const badgeValues = [];
  if (payload.role_title) {
    badgeValues.push(payload.role_title);
  }
  if (payload.speaker) {
    badgeValues.push(payload.speaker);
  }
  if (payload.analysis_source) {
    badgeValues.push(payload.analysis_source);
  }
  if (payload.recommended_status) {
    badgeValues.push(payload.recommended_status);
  }
  if (payload.reason) {
    badgeValues.push(payload.reason.replaceAll("_", " "));
  }
  if (payload.from_status) {
    badgeValues.push(`from ${humanizeToken(payload.from_status)}`);
  }
  if (payload.to_status) {
    badgeValues.push(`to ${humanizeToken(payload.to_status)}`);
  }

  return badgeValues
    .map((value) => `<span class="tag subdued-tag">${escapeHtml(value)}</span>`)
    .join("");
}

function humanizeAuditEvent(eventType) {
  return humanizeToken(eventType);
}

function humanizeToken(value) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

async function api(path, options = {}) {
  const { auth = true, headers = {}, ...rest } = options;
  const requestHeaders = {
    "Content-Type": "application/json",
    ...headers,
  };

  if (auth && state.authToken) {
    requestHeaders.Authorization = `Bearer ${state.authToken}`;
  }

  const response = await fetch(path, {
    headers: requestHeaders,
    ...rest,
  });

  if (!response.ok) {
    let detail = `Request failed with ${response.status}`;
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch (error) {
      detail = response.statusText || detail;
    }

    if (response.status === 401 && auth) {
      clearSession(false);
      renderAuthShell();
      setStatus("Your session expired. Sign in again.", true);
    }

    throw new Error(detail);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

function toList(rawValue) {
  return rawValue
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function optionalValue(value) {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function truncateText(value, maxLength) {
  if (value.length <= maxLength) {
    return value;
  }

  return `${value.slice(0, maxLength - 3)}...`;
}

function formatDate(value) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function setStatus(message, isError = false) {
  els.statusLine.textContent = message;
  els.statusLine.style.color = isError ? "var(--accent-deep)" : "var(--muted)";
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
