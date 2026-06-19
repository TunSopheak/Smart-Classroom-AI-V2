document.addEventListener("DOMContentLoaded", function () {
  if (window.location.pathname !== "/ai-monitoring") {
    return;
  }

  var snapshotCard = document.getElementById("iotCameraSnapshotCard");
  var lightCards = document.querySelectorAll(".iot-device-card");
  var insertAfter = snapshotCard || (lightCards.length >= 2 ? lightCards[1] : null);
  if (!insertAfter) {
    return;
  }

  var card = document.createElement("section");
  card.id = "iotAiDetectionCard";
  card.className = "iot-device-card";

  var header = document.createElement("div");
  header.className = "iot-device-header";

  var titleWrap = document.createElement("div");
  var title = document.createElement("h2");
  title.className = "iot-device-title";
  title.textContent = "AI Detection from Pi Camera";
  var subtitle = document.createElement("p");
  subtitle.className = "iot-device-subtitle";
  subtitle.textContent = "Analyze the latest Raspberry Pi camera snapshot and sync person count to occupancy.";
  titleWrap.appendChild(title);
  titleWrap.appendChild(subtitle);

  var analyzeButton = document.createElement("button");
  analyzeButton.type = "button";
  analyzeButton.className = "iot-refresh-btn";
  analyzeButton.textContent = "Analyze Latest Snapshot";
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

  addItem("AI Status", "iotAiStatus", "Not analyzed yet");
  addItem("Person Count", "iotAiPersonCount", "-");
  addItem("Phone Count", "iotAiPhoneCount", "-");
  addItem("Image Size", "iotAiImageSize", "-");
  addItem("Occupancy Sync", "iotAiOccupancySync", "Not synced yet");
  addItem("Synced Light", "iotAiSyncedLight", "-");
  addItem("Analyzed At", "iotAiAnalyzedAt", "-");

  var details = document.createElement("div");
  details.className = "helper-note";
  details.style.marginTop = "18px";
  details.innerHTML = '<strong>Detections</strong><pre id="iotAiDetections" style="white-space: pre-wrap; margin: 10px 0 0; font-size: 13px;">No detection result yet.</pre>';

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

function renderIotAnalysisState(state) {
  if (!state || !state.available) {
    return;
  }

  var analysis = state.analysis || {};
  var statusEl = document.getElementById("iotAiStatus");
  var personEl = document.getElementById("iotAiPersonCount");
  var phoneEl = document.getElementById("iotAiPhoneCount");
  var imageSizeEl = document.getElementById("iotAiImageSize");
  var occupancySyncEl = document.getElementById("iotAiOccupancySync");
  var syncedLightEl = document.getElementById("iotAiSyncedLight");
  var analyzedAtEl = document.getElementById("iotAiAnalyzedAt");
  var detectionsEl = document.getElementById("iotAiDetections");

  if (statusEl) statusEl.textContent = analysis.available ? "Completed" : "Unavailable";
  if (personEl) personEl.textContent = String(analysis.person_count ?? 0);
  if (phoneEl) phoneEl.textContent = String(analysis.phone_count ?? 0);
  if (imageSizeEl) imageSizeEl.textContent = (analysis.image_width || 0) + " x " + (analysis.image_height || 0);
  if (occupancySyncEl) occupancySyncEl.textContent = state.occupancy_synced ? "Synced" : (state.occupancy_error || "Not synced");
  if (syncedLightEl) syncedLightEl.textContent = state.occupancy?.light_status || state.light?.light_1_label || "-";
  if (analyzedAtEl) analyzedAtEl.textContent = state.analyzed_at || "-";

  updateOccupancyDashboard(state.occupancy);

  var detections = analysis.detections || [];
  if (detectionsEl) {
    if (!detections.length) {
      detectionsEl.textContent = "No person or phone detected.";
    } else {
      detectionsEl.textContent = detections
        .map(function (item, index) {
          return (index + 1) + ". " + item.label + " | confidence: " + item.confidence + " | box: [" + item.box.join(", ") + "]";
        })
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
