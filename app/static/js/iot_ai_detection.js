document.addEventListener("DOMContentLoaded", function () {
  if (window.location.pathname !== "/ai-monitoring") {
    return;
  }

  var snapshotCard = document.getElementById("snapshot-preview");
  var lightCards = document.querySelectorAll(".iot-device-card");
  var insertAfter = snapshotCard || (lightCards.length >= 2 ? lightCards[1] : null);
  if (!insertAfter) {
    return;
  }

  var card = document.createElement("section");
  card.id = "iot-ai-results";
  card.className = "iot-device-card anchor-section";

  var header = document.createElement("div");
  header.className = "iot-device-header";

  var titleWrap = document.createElement("div");
  var title = document.createElement("h2");
  title.className = "iot-device-title";
  title.textContent = "Latest AI Sample Analysis";
  var subtitle = document.createElement("p");
  subtitle.className = "iot-device-subtitle";
  subtitle.textContent = "Review the latest sampled behavior-overlay result and occupancy synchronization. This is sampled AI, not continuous frame-by-frame inference.";
  titleWrap.appendChild(title);
  titleWrap.appendChild(subtitle);

  var analyzeButton = document.createElement("button");
  analyzeButton.type = "button";
  analyzeButton.className = "iot-refresh-btn";
  analyzeButton.textContent = "Analyze Latest Sample";
  analyzeButton.addEventListener("click", analyzeLatestIotSnapshot);

  header.appendChild(titleWrap);
  header.appendChild(analyzeButton);

  var grid = document.createElement("div");
  grid.className = "iot-device-grid";

  function addItem(label, id, text) {
    var item = document.createElement("div");
    item.className = "iot-device-item";
    var labelEl = document.createElement("span");
    labelEl.className = "iot-device-label";
    labelEl.textContent = label;
    var valueEl = document.createElement("span");
    valueEl.id = id;
    valueEl.className = "iot-device-value";
    valueEl.textContent = text;
    item.appendChild(labelEl);
    item.appendChild(valueEl);
    grid.appendChild(item);
  }

  addItem("AI Sampling", "iotAiStatus", "Waiting");
  addItem("Person Count", "iotAiPersonCount", "-");
  addItem("Phone Count", "iotAiPhoneCount", "-");
  addItem("Behavior Warnings", "iotAiBehaviorWarnings", "-");
  addItem("Image Size", "iotAiImageSize", "-");
  addItem("Session Sync", "iotAiOccupancySync", "Skipped until active session");
  addItem("Synced Light", "iotAiSyncedLight", "-");
  addItem("Analyzed At", "iotAiAnalyzedAt", "-");

  var details = document.createElement("div");
  details.className = "helper-note iot-detection-details";
  details.innerHTML = '<strong>Behavior Overlay Detections</strong><pre id="iotAiDetections" class="iot-detection-output">No detection result yet.</pre>';

  card.appendChild(header);
  card.appendChild(grid);
  card.appendChild(details);

  insertAfter.insertAdjacentElement("afterend", card);
  refreshLatestIotAnalysisState();
  window.setInterval(refreshLatestIotAnalysisState, 10000);
});

function getSelectedAiMonitoringSessionId() {
  var params = new URLSearchParams(window.location.search);
  var sessionId = params.get("session_id");
  if (sessionId) {
    return sessionId;
  }

  var selector = document.querySelector('select[name="session_id"]');
  if (selector && selector.value) {
    return selector.value;
  }

  return "";
}

function updateOccupancyDashboard(occupancy) {
  if (!occupancy) {
    return;
  }

  var detectedCount = document.getElementById("detected-count");
  var difference = document.getElementById("count-difference");
  var occupancyStatus = document.getElementById("occupancy-status");
  var lightStatus = document.getElementById("light-status");

  if (detectedCount) detectedCount.textContent = occupancy.detected_count_label || "Unknown";
  if (difference) difference.textContent = occupancy.difference_label || "Unknown";
  if (occupancyStatus) occupancyStatus.textContent = occupancy.occupancy_status || "Unknown";
  if (lightStatus) lightStatus.textContent = occupancy.light_status || "Auto Mode";
}

function detectionBehaviorText(item, index) {
  var track = item.student_label || (item.track_id ? "Student " + item.track_id : "Object " + (index + 1));
  var label = item.behavior_label || item.overlay_label || item.label || "Object Detected";
  var risk = item.risk || "info";
  var confidence = item.confidence;
  var confidenceText = confidence === undefined || confidence === null ? "unknown" : confidence;
  var box = Array.isArray(item.box) ? item.box.join(", ") : "-";
  var reason = item.behavior_reason || "No behavior-specific reason recorded.";
  return track + " | " + label + " | risk: " + risk + " | confidence: " + confidenceText + " | box: [" + box + "] | " + reason;
}

function renderIotAnalysisState(state) {
  if (!state || !state.available) {
    var waitingStatusEl = document.getElementById("iotAiStatus");
    var waitingSyncEl = document.getElementById("iotAiOccupancySync");
    if (waitingStatusEl) waitingStatusEl.textContent = "Waiting";
    if (waitingSyncEl) waitingSyncEl.textContent = "Skipped until an active sample is analyzed";
    if (typeof window.updateDemoReadinessItem === "function") {
      window.updateDemoReadinessItem("demoReadyAi", "Waiting", "neutral", "No completed sample yet");
      window.updateDemoReadinessItem("demoReadyOccupancy", "Skipped", "neutral", state?.session_sync_message || "Waiting for active session");
    }
    return;
  }

  var analysis = state.analysis || {};
  var statusEl = document.getElementById("iotAiStatus");
  var personEl = document.getElementById("iotAiPersonCount");
  var phoneEl = document.getElementById("iotAiPhoneCount");
  var behaviorWarningsEl = document.getElementById("iotAiBehaviorWarnings");
  var imageSizeEl = document.getElementById("iotAiImageSize");
  var occupancySyncEl = document.getElementById("iotAiOccupancySync");
  var syncedLightEl = document.getElementById("iotAiSyncedLight");
  var analyzedAtEl = document.getElementById("iotAiAnalyzedAt");
  var detectionsEl = document.getElementById("iotAiDetections");

  var aiCompleted = analysis.available !== false;
  if (statusEl) statusEl.textContent = aiCompleted ? "Completed" : "Waiting";
  if (personEl) personEl.textContent = String(analysis.person_count ?? 0);
  if (phoneEl) phoneEl.textContent = String(analysis.phone_count ?? 0);
  var behaviorCounts = analysis.behavior_summary?.counts || {};
  var warningCount = Number(behaviorCounts.possible_phone_usage || 0) + Number(behaviorCounts.possible_head_down || 0) + Number(behaviorCounts.possible_inattentive || 0);
  if (behaviorWarningsEl) behaviorWarningsEl.textContent = String(warningCount);
  if (imageSizeEl) imageSizeEl.textContent = (analysis.image_width || 0) + " x " + (analysis.image_height || 0);
  if (occupancySyncEl) {
    var sessionSyncLabel = state.session_sync_status === "active"
      ? "Active"
      : (state.session_sync_status === "not_active" ? "Not Active" : "Skipped");
    occupancySyncEl.textContent = sessionSyncLabel + " — " + (state.session_sync_message || state.occupancy_error || "Not synced");
  }
  if (syncedLightEl) syncedLightEl.textContent = state.occupancy?.light_status || state.light?.light_1_label || "-";
  if (analyzedAtEl) analyzedAtEl.textContent = state.analyzed_at || "-";

  if (typeof window.updateDemoReadinessItem === "function") {
    window.updateDemoReadinessItem(
      "demoReadyAi",
      aiCompleted ? "Completed" : "Waiting",
      aiCompleted ? "ready" : "neutral",
      aiCompleted ? (state.analyzed_at || "Analysis timestamp unavailable") : "Detector result unavailable; waiting for next sample"
    );
    var syncMode = state.session_sync_status === "active"
      ? "ready"
      : (state.session_sync_status === "not_active" ? "warning" : "neutral");
    var syncValue = state.session_sync_status === "active"
      ? "Ready"
      : (state.session_sync_status === "not_active" ? "Not Active" : "Skipped");
    window.updateDemoReadinessItem(
      "demoReadyOccupancy",
      syncValue,
      syncMode,
      state.session_sync_message || "Waiting for active session"
    );
  }

  updateOccupancyDashboard(state.occupancy);

  var detections = analysis.detections || [];
  if (detectionsEl) {
    if (!detections.length) {
      detectionsEl.textContent = "No person, phone, or behavior object detected.";
    } else {
      detectionsEl.textContent = detections
        .map(detectionBehaviorText)
        .join("\n");
    }
  }
}

async function refreshLatestIotAnalysisState() {
  try {
    var response = await fetch("/iot/camera/latest", { cache: "no-store" });
    var data = await response.json();
    renderIotAnalysisState(data.analysis_state);
  } catch (error) {
    // Keep the current dashboard state if polling fails.
  }
}

async function analyzeLatestIotSnapshot() {
  var statusEl = document.getElementById("iotAiStatus");
  var occupancySyncEl = document.getElementById("iotAiOccupancySync");
  var detectionsEl = document.getElementById("iotAiDetections");

  if (!statusEl) {
    return;
  }

  statusEl.textContent = "Analyzing...";
  if (occupancySyncEl) occupancySyncEl.textContent = "Waiting...";
  if (detectionsEl) detectionsEl.textContent = "Please wait...";

  try {
    var response = await fetch("/iot/camera/analyze-latest", {
      method: "POST",
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        session_id: getSelectedAiMonitoringSessionId(),
      }),
    });
    var data = await response.json();

    if (!response.ok || !data.ok) {
      throw new Error(data.message || "AI analysis failed");
    }

    renderIotAnalysisState(data.analysis_state);

    if (typeof refreshIotLightStatus === "function") {
      await refreshIotLightStatus();
    }
    if (typeof refreshIotDeviceStatus === "function") {
      await refreshIotDeviceStatus();
    }
  } catch (error) {
    statusEl.textContent = "Failed";
    if (occupancySyncEl) occupancySyncEl.textContent = "Failed";
    if (detectionsEl) detectionsEl.textContent = error.message || "AI analysis failed.";
  }
}
