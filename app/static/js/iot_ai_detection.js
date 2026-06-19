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
  subtitle.textContent = "Analyze the latest Raspberry Pi camera snapshot with the backend YOLO engine.";
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

  var details = document.createElement("div");
  details.className = "helper-note";
  details.style.marginTop = "18px";
  details.innerHTML = '<strong>Detections</strong><pre id="iotAiDetections" style="white-space: pre-wrap; margin: 10px 0 0; font-size: 13px;">No detection result yet.</pre>';

  card.appendChild(header);
  card.appendChild(grid);
  card.appendChild(details);

  insertAfter.insertAdjacentElement("afterend", card);
});

async function analyzeLatestIotSnapshot() {
  var statusEl = document.getElementById("iotAiStatus");
  var personEl = document.getElementById("iotAiPersonCount");
  var phoneEl = document.getElementById("iotAiPhoneCount");
  var imageSizeEl = document.getElementById("iotAiImageSize");
  var detectionsEl = document.getElementById("iotAiDetections");

  if (!statusEl) {
    return;
  }

  statusEl.textContent = "Analyzing...";
  if (detectionsEl) detectionsEl.textContent = "Please wait...";

  try {
    var response = await fetch("/iot/camera/analyze-latest", {
      method: "POST",
      cache: "no-store",
    });
    var data = await response.json();

    if (!response.ok || !data.ok) {
      throw new Error(data.message || "AI analysis failed");
    }

    var analysis = data.analysis || {};
    statusEl.textContent = analysis.available ? "Completed" : "Unavailable";
    if (personEl) personEl.textContent = String(analysis.person_count ?? 0);
    if (phoneEl) phoneEl.textContent = String(analysis.phone_count ?? 0);
    if (imageSizeEl) {
      imageSizeEl.textContent = (analysis.image_width || 0) + " x " + (analysis.image_height || 0);
    }

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
  } catch (error) {
    statusEl.textContent = "Failed";
    if (detectionsEl) detectionsEl.textContent = error.message || "AI analysis failed.";
  }
}
