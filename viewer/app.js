const ownerColors = ["#ff243f", "#f7f7f7", "#ff9aa5", "#8b0018"];
const neutralColor = "#d8d6d2";
const detectorLabels = {
  bad_launch_sun_lane: "Bad launch lane",
  sun_death: "Fleet crossed sun",
  missed_comet_window: "Missed comet window",
  slow_expansion: "Slow expansion",
  idle_overstock: "Idle overstock",
  fleet_disappeared_without_capture: "Fleet vanished without gain",
  late_trailing_no_pressure: "Late no pressure",
  overdefended_low_production: "Overdefended low value",
  crash: "Agent crash",
  slow_match: "Slow match",
  slot_bias: "Slot bias",
};

const elements = {
  canvas: document.getElementById("boardCanvas"),
  fileInput: document.getElementById("fileInput"),
  sampleButton: document.getElementById("sampleButton"),
  fitButton: document.getElementById("fitButton"),
  prevButton: document.getElementById("prevButton"),
  playButton: document.getElementById("playButton"),
  nextButton: document.getElementById("nextButton"),
  stepSlider: document.getElementById("stepSlider"),
  speedSelect: document.getElementById("speedSelect"),
  labelsToggle: document.getElementById("labelsToggle"),
  trailsToggle: document.getElementById("trailsToggle"),
  nextIssueButton: document.getElementById("nextIssueButton"),
  exportNotesButton: document.getElementById("exportNotesButton"),
  addNoteButton: document.getElementById("addNoteButton"),
  noteCategory: document.getElementById("noteCategory"),
  noteText: document.getElementById("noteText"),
  stepReadout: document.getElementById("stepReadout"),
  phaseReadout: document.getElementById("phaseReadout"),
  winnerReadout: document.getElementById("winnerReadout"),
  matchSubtitle: document.getElementById("matchSubtitle"),
  matchSummary: document.getElementById("matchSummary"),
  comparePanel: document.getElementById("comparePanel"),
  insightPanel: document.getElementById("insightPanel"),
  flawSignalPanel: document.getElementById("flawSignalPanel"),
  metricsTable: document.getElementById("metricsTable"),
  issueList: document.getElementById("issueList"),
  noteList: document.getElementById("noteList"),
};

const ctx = elements.canvas.getContext("2d");
const state = {
  replay: null,
  frameIndex: 0,
  notes: [],
  playing: false,
  timer: null,
  animationStart: performance.now(),
};

function fallbackSample() {
  return {
    schema_version: 1,
    game: "orbit_wars",
    match_id: "sample_cherry_lab",
    run_id: "viewer_sample",
    matchup: "candidate_vs_baseline",
    seed: 42,
    player_count: 2,
    agents: ["candidate", "baseline"],
    rewards: [1, -1],
    statuses: ["DONE", "DONE"],
    winner_slot: 0,
    board: { size: 100, center: [50, 50], sun_radius: 10 },
    issues: [
      { detector: "slow_expansion", severity: "P2", message: "Candidate waited too long before second capture.", match_id: "sample_cherry_lab", step: 3, slot: 0, evidence: { planets: 1 } }
    ],
    notes: [],
    frames: [
      frame(0, [[0, 0, 18, 25, 2.1, 10, 3], [1, 1, 82, 75, 2.1, 10, 3], [2, -1, 39, 44, 1.7, 18, 4], [3, -1, 61, 56, 1.7, 18, 4]], []),
      frame(1, [[0, 0, 18, 25, 2.1, 13, 3], [1, 1, 82, 75, 2.1, 13, 3], [2, -1, 39, 44, 1.7, 18, 4], [3, -1, 61, 56, 1.7, 18, 4]], [[0, 0, 24, 29, 0.52, 0, 6]]),
      frame(2, [[0, 0, 18, 25, 2.1, 16, 3], [1, 1, 82, 75, 2.1, 16, 3], [2, -1, 39, 44, 1.7, 18, 4], [3, -1, 61, 56, 1.7, 18, 4]], [[0, 0, 30, 33, 0.52, 0, 6], [1, 1, 76, 71, -2.62, 1, 6]]),
      frame(3, [[0, 0, 18, 25, 2.1, 19, 3], [1, 1, 82, 75, 2.1, 19, 3], [2, 0, 39, 44, 1.7, 5, 4], [3, -1, 61, 56, 1.7, 18, 4]], [[1, 1, 70, 67, -2.62, 1, 6]]),
      frame(4, [[0, 0, 18, 25, 2.1, 22, 3], [1, 1, 82, 75, 2.1, 22, 3], [2, 0, 39, 44, 1.7, 9, 4], [3, -1, 61, 56, 1.7, 18, 4]], [[2, 0, 44, 48, 0.45, 2, 5], [1, 1, 64, 63, -2.62, 1, 6]]),
      frame(5, [[0, 0, 18, 25, 2.1, 25, 3], [1, 1, 82, 75, 2.1, 25, 3], [2, 0, 39, 44, 1.7, 13, 4], [3, 1, 61, 56, 1.7, 4, 4]], [[2, 0, 50, 52, 0.45, 2, 5]])
    ]
  };
}

function frame(step, planets, fleets) {
  const metrics = [0, 1].map((slot) => {
    const ownedPlanets = planets.filter((planet) => planet[1] === slot);
    const ownedFleets = fleets.filter((fleet) => fleet[1] === slot);
    const shipsOnPlanets = ownedPlanets.reduce((sum, planet) => sum + planet[5], 0);
    const shipsInFleets = ownedFleets.reduce((sum, fleet) => sum + fleet[6], 0);
    return {
      match_id: "sample_cherry_lab",
      step,
      slot,
      planets: ownedPlanets.length,
      ships_on_planets: shipsOnPlanets,
      ships_in_fleets: shipsInFleets,
      total_ships: shipsOnPlanets + shipsInFleets,
      production: ownedPlanets.reduce((sum, planet) => sum + planet[6], 0),
      fleets: ownedFleets.length
    };
  });
  return { step, planets, fleets, comets: [], comet_planet_ids: [], metrics, actions: [] };
}

async function loadSample() {
  try {
    const response = await fetch("sample-viewer-replay.json", { cache: "no-store" });
    if (!response.ok) throw new Error("sample fetch failed");
    loadReplay(await response.json());
  } catch {
    loadReplay(fallbackSample());
  }
}

async function loadReplayFromUrl(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error(`Replay fetch failed: ${response.status}`);
  loadReplay(await response.json());
}

function loadReplay(replay) {
  state.replay = replay;
  state.frameIndex = 0;
  state.notes = Array.isArray(replay.notes) ? [...replay.notes] : [];
  elements.stepSlider.max = Math.max(0, (replay.frames || []).length - 1);
  elements.stepSlider.value = 0;
  elements.matchSubtitle.textContent = `${replay.matchup || replay.match_id} | seed ${replay.seed} | ${replay.agents.join(" vs ")}`;
  renderAll();
}

function currentFrame() {
  if (!state.replay || !state.replay.frames.length) return null;
  return state.replay.frames[state.frameIndex];
}

function phaseForStep(step) {
  if (step < 120) return "early";
  if (step < 300) return "mid";
  return "late";
}

function ownerName(slot) {
  if (!state.replay || slot < 0) return "Neutral";
  return state.replay.agents[slot] || `Slot ${slot}`;
}

function ownerColor(owner) {
  return owner < 0 ? neutralColor : ownerColors[owner % ownerColors.length];
}

function fitCanvas() {
  const rect = elements.canvas.getBoundingClientRect();
  const scale = window.devicePixelRatio || 1;
  elements.canvas.width = Math.max(1, Math.floor(rect.width * scale));
  elements.canvas.height = Math.max(1, Math.floor(rect.height * scale));
  drawBoard();
}

function boardTransform() {
  const replay = state.replay || fallbackSample();
  const boardSize = replay.board?.size || 100;
  const width = elements.canvas.width;
  const height = elements.canvas.height;
  const pad = Math.min(width, height) * 0.055;
  const side = Math.min(width, height) - pad * 2;
  const left = (width - side) / 2;
  const top = (height - side) / 2;
  return {
    x: (value) => left + (value / boardSize) * side,
    y: (value) => top + (value / boardSize) * side,
    r: (value) => (value / boardSize) * side,
    left,
    top,
    side,
  };
}

function drawBoard() {
  const frameData = currentFrame();
  const replay = state.replay;
  const width = elements.canvas.width;
  const height = elements.canvas.height;
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#030304";
  ctx.fillRect(0, 0, width, height);
  drawGrid();
  if (!frameData || !replay) {
    drawEmpty();
    return;
  }

  const tx = boardTransform();
  const pulse = 0.65 + 0.35 * Math.sin((performance.now() - state.animationStart) / 420);
  const center = replay.board?.center || [50, 50];
  const sunRadius = replay.board?.sun_radius || 10;

  drawOrbitRings(tx, center);
  drawSun(tx, center, sunRadius, pulse);
  if (elements.trailsToggle.checked) drawFleetTrails(tx, frameData.fleets || []);
  drawPlanets(tx, frameData, pulse);
  drawFleets(tx, frameData.fleets || [], pulse);
}

function drawGrid() {
  const tx = boardTransform();
  ctx.save();
  ctx.strokeStyle = "rgba(255,255,255,0.035)";
  ctx.lineWidth = Math.max(1, elements.canvas.width / 900);
  for (let i = 0; i <= 10; i += 1) {
    const p = tx.left + (i / 10) * tx.side;
    ctx.beginPath();
    ctx.moveTo(p, tx.top);
    ctx.lineTo(p, tx.top + tx.side);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(tx.left, p);
    ctx.lineTo(tx.left + tx.side, p);
    ctx.stroke();
  }
  ctx.strokeStyle = "rgba(255,111,126,0.28)";
  ctx.strokeRect(tx.left, tx.top, tx.side, tx.side);
  ctx.restore();
}

function drawEmpty() {
  ctx.save();
  ctx.fillStyle = "rgba(248,244,244,0.72)";
  ctx.textAlign = "center";
  ctx.font = `${Math.max(16, elements.canvas.width / 42)}px sans-serif`;
  ctx.fillText("Load a replay JSON or press Sample", elements.canvas.width / 2, elements.canvas.height / 2);
  ctx.restore();
}

function drawOrbitRings(tx, center) {
  ctx.save();
  ctx.strokeStyle = "rgba(255,111,126,0.12)";
  ctx.lineWidth = Math.max(1, elements.canvas.width / 700);
  [18, 28, 40].forEach((radius) => {
    ctx.beginPath();
    ctx.arc(tx.x(center[0]), tx.y(center[1]), tx.r(radius), 0, Math.PI * 2);
    ctx.stroke();
  });
  ctx.restore();
}

function drawSun(tx, center, radius, pulse) {
  const cx = tx.x(center[0]);
  const cy = tx.y(center[1]);
  const r = tx.r(radius);
  const glow = r * (1.35 + pulse * 0.2);
  const gradient = ctx.createRadialGradient(cx, cy, r * 0.18, cx, cy, glow);
  gradient.addColorStop(0, "rgba(255,255,255,0.98)");
  gradient.addColorStop(0.25, "rgba(255,111,126,0.92)");
  gradient.addColorStop(0.55, "rgba(225,6,44,0.46)");
  gradient.addColorStop(1, "rgba(225,6,44,0)");
  ctx.save();
  ctx.fillStyle = gradient;
  ctx.beginPath();
  ctx.arc(cx, cy, glow, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "rgba(255,255,255,0.86)";
  ctx.lineWidth = Math.max(1.5, elements.canvas.width / 420);
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.stroke();
  ctx.restore();
}

function drawPlanets(tx, frameData, pulse) {
  const cometIds = new Set((frameData.comet_planet_ids || []).map((id) => Number(id)));
  const issueSlots = new Set(nearbyIssues().map((issue) => issue.slot).filter((slot) => slot !== null && slot !== undefined));
  (frameData.planets || []).forEach((planet) => {
    const [id, owner, x, y, radius, ships, production] = planet;
    const cx = tx.x(x);
    const cy = tx.y(y);
    const pr = Math.max(tx.r(radius), 5);
    const color = ownerColor(owner);
    ctx.save();
    ctx.shadowColor = color;
    ctx.shadowBlur = owner >= 0 ? 18 + pulse * 10 : 4;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(cx, cy, pr, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.lineWidth = Math.max(1.2, elements.canvas.width / 580);
    ctx.strokeStyle = issueSlots.has(owner) ? "#ffffff" : "rgba(255,255,255,0.72)";
    ctx.stroke();
    ctx.strokeStyle = cometIds.has(Number(id)) ? "#ff6f7e" : "rgba(225,6,44,0.65)";
    ctx.lineWidth = Math.max(1, elements.canvas.width / 760);
    ctx.beginPath();
    ctx.arc(cx, cy, pr + 4 + production * 0.5, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * Math.min(1, production / 5));
    ctx.stroke();
    if (elements.labelsToggle.checked) {
      ctx.fillStyle = owner === 1 ? "#050506" : "#f8f4f4";
      ctx.font = `${Math.max(10, elements.canvas.width / 72)}px sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(String(Math.round(ships)), cx, cy);
    }
    ctx.restore();
  });
}

function drawFleetTrails(tx, fleets) {
  ctx.save();
  fleets.forEach((fleet) => {
    const [, owner, x, y, angle, , ships] = fleet;
    const speedLine = Math.min(9, 2 + Number(ships) / 12);
    const cx = tx.x(x);
    const cy = tx.y(y);
    const length = tx.r(speedLine);
    ctx.strokeStyle = ownerColor(owner);
    ctx.globalAlpha = 0.24;
    ctx.lineWidth = Math.max(2, elements.canvas.width / 520);
    ctx.beginPath();
    ctx.moveTo(cx - Math.cos(angle) * length, cy - Math.sin(angle) * length);
    ctx.lineTo(cx, cy);
    ctx.stroke();
  });
  ctx.restore();
}

function drawFleets(tx, fleets, pulse) {
  ctx.save();
  fleets.forEach((fleet) => {
    const [, owner, x, y, angle, , ships] = fleet;
    const cx = tx.x(x);
    const cy = tx.y(y);
    const size = Math.max(4, Math.min(13, 4 + Math.sqrt(Number(ships))));
    ctx.translate(cx, cy);
    ctx.rotate(angle);
    ctx.fillStyle = ownerColor(owner);
    ctx.shadowColor = ownerColor(owner);
    ctx.shadowBlur = 10 + pulse * 8;
    ctx.beginPath();
    ctx.moveTo(size * 1.5, 0);
    ctx.lineTo(-size, size * 0.72);
    ctx.lineTo(-size * 0.55, 0);
    ctx.lineTo(-size, -size * 0.72);
    ctx.closePath();
    ctx.fill();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
  });
  ctx.restore();
}

function renderAll() {
  const replay = state.replay;
  const frameData = currentFrame();
  if (!replay || !frameData) {
    fitCanvas();
    return;
  }
  elements.stepReadout.textContent = `${frameData.step} / ${replay.frames.length - 1}`;
  elements.phaseReadout.textContent = phaseForStep(frameData.step);
  elements.winnerReadout.textContent = replay.winner_slot === null || replay.winner_slot === undefined ? "-" : ownerName(replay.winner_slot);
  elements.stepSlider.value = state.frameIndex;
  renderSummary(replay);
  renderComparePanel(frameData);
  renderInsightPanel(frameData);
  renderFlawSignals();
  renderMetrics(frameData);
  renderIssues();
  renderNotes();
  fitCanvas();
}

function renderSummary(replay) {
  const rows = [
    ["Match", replay.match_id],
    ["Seed", replay.seed],
    ["Agents", replay.agents.join(" vs ")],
    ["Status", replay.statuses.join(" / ")],
    ["Reward", replay.rewards.join(" / ")],
  ];
  elements.matchSummary.innerHTML = rows.map(([key, value]) => `<dt>${escapeHtml(key)}</dt><dd>${escapeHtml(String(value ?? "-"))}</dd>`).join("");
}

function buildFrameComparison(frameData) {
  const metrics = frameData.metrics || [];
  if (!metrics.length) return [];
  const bestShips = Math.max(...metrics.map((metric) => Number(metric.total_ships || 0)));
  return metrics.map((metric) => ({
    slot: metric.slot,
    shipDelta: Number(metric.total_ships || 0) - bestShips,
    production: Number(metric.production || 0),
    planets: Number(metric.planets || 0),
    fleets: Number(metric.fleets || 0),
    pressure: Number(metric.ships_in_fleets || 0),
  }));
}

function renderComparePanel(frameData) {
  const rows = buildFrameComparison(frameData);
  if (!rows.length) {
    elements.comparePanel.innerHTML = `<div class="compare-row"><strong>No compare data</strong><span>-</span></div>`;
    return;
  }
  elements.comparePanel.innerHTML = rows.map((row) => {
    const deltaClass = row.shipDelta >= 0 ? "delta-positive" : "delta-negative";
    const deltaText = row.shipDelta === 0 ? "leader" : `${row.shipDelta.toFixed(0)} ships`;
    return `<div class="compare-row">
      <div><strong>${escapeHtml(ownerName(row.slot))}</strong><span>${row.planets} planets | ${row.production} prod | ${row.pressure.toFixed(0)} transit</span></div>
      <strong class="${deltaClass}">${escapeHtml(deltaText)}</strong>
    </div>`;
  }).join("");
}

function metricLeader(frameData, key) {
  const metrics = frameData.metrics || [];
  if (!metrics.length) return null;
  return metrics.reduce((best, metric) => Number(metric[key] || 0) > Number(best[key] || 0) ? metric : best, metrics[0]);
}

function renderInsightPanel(frameData) {
  const derived = frameData.derived || {};
  const leader = derived.leader_slot ?? metricLeader(frameData, "total_ships")?.slot;
  const prodLeader = derived.production_leader_slot ?? metricLeader(frameData, "production")?.slot;
  const planetLeader = derived.planet_leader_slot ?? metricLeader(frameData, "planets")?.slot;
  const pressureLeader = derived.pressure_leader_slot ?? metricLeader(frameData, "ships_in_fleets")?.slot;
  const shipSpread = Number(derived.ship_spread ?? 0);
  const severityCounts = state.replay?.analysis?.severity_counts || {};
  const totalIssues = Number(state.replay?.analysis?.total_issues || 0);
  const cards = [
    ["Leader", ownerName(Number(leader)), `${shipSpread.toFixed(0)} ship spread`],
    ["Production edge", ownerName(Number(prodLeader)), "best current income"],
    ["Map control", ownerName(Number(planetLeader)), "most owned planets"],
    ["Pressure", ownerName(Number(pressureLeader)), "most ships in transit"],
    ["Auto flags", `${totalIssues}`, `P1 ${severityCounts.P1 || 0} | P2 ${severityCounts.P2 || 0} | P3 ${severityCounts.P3 || 0}`],
  ];
  elements.insightPanel.innerHTML = cards.map(([title, value, meta]) => `<div class="insight-card">
    <strong>${escapeHtml(title)}: ${escapeHtml(value)}</strong>
    <span>${escapeHtml(meta)}</span>
  </div>`).join("");
}

function renderMetrics(frameData) {
  const headers = `<div class="metric-row"><strong>Slot</strong><strong class="metric-value">Planets</strong><strong class="metric-value">Prod</strong><strong class="metric-value">Ships</strong><strong class="metric-value">Fleets</strong><strong class="metric-value">Transit</strong></div>`;
  const rows = (frameData.metrics || []).map((metric) => {
    const color = ownerColor(metric.slot);
    return `<div class="metric-row">
      <div class="metric-name"><span class="swatch" style="color:${color};background:${color}"></span><span>${escapeHtml(ownerName(metric.slot))}</span></div>
      <span class="metric-value">${metric.planets}</span>
      <span class="metric-value">${metric.production}</span>
      <span class="metric-value">${Number(metric.total_ships ?? 0).toFixed(0)}</span>
      <span class="metric-value">${metric.fleets}</span>
      <span class="metric-value">${Number(metric.ships_in_fleets ?? 0).toFixed(0)}</span>
    </div>`;
  }).join("");
  elements.metricsTable.innerHTML = headers + rows;
}

function detectorLabel(detector) {
  return detectorLabels[detector] || detector || "Issue";
}

function nearbyIssues() {
  if (!state.replay) return [];
  const frameData = currentFrame();
  if (!frameData) return [];
  return (state.replay.issues || []).filter((issue) => issue.step === null || issue.step === undefined || Math.abs(Number(issue.step) - Number(frameData.step)) <= 8);
}

function renderFlawSignals() {
  const issues = nearbyIssues();
  if (!issues.length) {
    elements.flawSignalPanel.innerHTML = `<div class="flaw-card"><strong>Clean nearby window</strong><span>No automatic flaw flags within 8 turns.</span></div>`;
    return;
  }
  elements.flawSignalPanel.innerHTML = issues.slice(0, 4).map((issue) => `<button class="flaw-card ${escapeHtml(String(issue.severity || "").toLowerCase())}" type="button" data-step="${issue.step ?? state.frameIndex}">
    <strong>${escapeHtml(detectorLabel(issue.detector))}</strong>
    <span>${escapeHtml(issue.severity || "P?")} | step ${escapeHtml(String(issue.step ?? "-"))} | slot ${escapeHtml(String(issue.slot ?? "-"))}</span>
  </button>`).join("");
  elements.flawSignalPanel.querySelectorAll(".flaw-card").forEach((node) => {
    node.addEventListener("click", () => setFrame(Number(node.dataset.step || 0)));
  });
}

function renderIssues() {
  const issues = nearbyIssues();
  if (!issues.length) {
    elements.issueList.innerHTML = `<div class="issue-item"><strong>No nearby issues</strong><span>Scrub or jump to inspect flagged turns.</span></div>`;
    return;
  }
  elements.issueList.innerHTML = issues.map((issue) => `<button class="issue-item" type="button" data-step="${issue.step ?? state.frameIndex}">
    <strong>${escapeHtml(issue.severity || "P?")} ${escapeHtml(detectorLabel(issue.detector))}</strong>
    <span>Step ${escapeHtml(String(issue.step ?? "-"))} | Slot ${escapeHtml(String(issue.slot ?? "-"))}</span>
    <div>${escapeHtml(issue.message || "")}</div>
  </button>`).join("");
  elements.issueList.querySelectorAll(".issue-item").forEach((node) => {
    node.addEventListener("click", () => setFrame(Number(node.dataset.step || 0)));
  });
}

function renderNotes() {
  if (!state.notes.length) {
    elements.noteList.innerHTML = `<div class="note-item"><strong>No notes yet</strong><span>Add observations while watching the replay.</span></div>`;
    return;
  }
  elements.noteList.innerHTML = state.notes.slice().reverse().map((note) => `<div class="note-item">
    <strong>${escapeHtml(note.category || "note")} at step ${escapeHtml(String(note.step ?? "-"))}</strong>
    <span>${escapeHtml(note.created_at || "")}</span>
    <div>${escapeHtml(note.text || "")}</div>
  </div>`).join("");
}

function setFrame(index) {
  if (!state.replay) return;
  state.frameIndex = Math.max(0, Math.min(index, state.replay.frames.length - 1));
  renderAll();
}

function togglePlay() {
  state.playing = !state.playing;
  elements.playButton.textContent = state.playing ? "Pause" : "Play";
  if (state.playing) {
    state.timer = window.setInterval(() => {
      if (!state.replay) return;
      setFrame((state.frameIndex + 1) % state.replay.frames.length);
    }, Number(elements.speedSelect.value));
  } else {
    window.clearInterval(state.timer);
  }
}

function nextIssue() {
  if (!state.replay) return;
  const issueSteps = (state.replay.issues || [])
    .map((issue) => Number(issue.step))
    .filter((step) => Number.isFinite(step))
    .sort((a, b) => a - b);
  if (!issueSteps.length) return;
  const next = issueSteps.find((step) => step > currentFrame().step) ?? issueSteps[0];
  setFrame(next);
}

function addNote() {
  const text = elements.noteText.value.trim();
  if (!text) return;
  state.notes.push({
    step: currentFrame()?.step ?? state.frameIndex,
    category: elements.noteCategory.value,
    text,
    created_at: new Date().toISOString(),
  });
  elements.noteText.value = "";
  renderNotes();
}

function exportNotes() {
  const payload = JSON.stringify({ match_id: state.replay?.match_id || "", notes: state.notes }, null, 2);
  const blob = new Blob([payload], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${state.replay?.match_id || "orbit-wars"}-notes.json`;
  link.click();
  URL.revokeObjectURL(url);
}

function escapeHtml(value) {
  return value.replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
}

elements.fileInput.addEventListener("change", async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;
  loadReplay(JSON.parse(await file.text()));
});
elements.sampleButton.addEventListener("click", loadSample);
elements.fitButton.addEventListener("click", fitCanvas);
elements.prevButton.addEventListener("click", () => setFrame(state.frameIndex - 1));
elements.nextButton.addEventListener("click", () => setFrame(state.frameIndex + 1));
elements.playButton.addEventListener("click", togglePlay);
elements.stepSlider.addEventListener("input", () => setFrame(Number(elements.stepSlider.value)));
elements.speedSelect.addEventListener("change", () => {
  if (state.playing) {
    togglePlay();
    togglePlay();
  }
});
elements.labelsToggle.addEventListener("change", drawBoard);
elements.trailsToggle.addEventListener("change", drawBoard);
elements.nextIssueButton.addEventListener("click", nextIssue);
elements.addNoteButton.addEventListener("click", addNote);
elements.exportNotesButton.addEventListener("click", exportNotes);
window.addEventListener("resize", fitCanvas);

function animationLoop() {
  drawBoard();
  requestAnimationFrame(animationLoop);
}

const replayParam = new URLSearchParams(window.location.search).get("replay");
if (replayParam) {
  loadReplayFromUrl(replayParam).catch(loadSample);
} else {
  loadSample();
}
animationLoop();
