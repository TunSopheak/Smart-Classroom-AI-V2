document.addEventListener("DOMContentLoaded", function () {
  if (window.location.pathname !== "/ai-monitoring") {
    return;
  }

  var lightCards = document.querySelectorAll(".iot-device-card");
  if (lightCards.length < 2) {
    return;
  }

  var card = document.createElement("section");
  card.id = "snapshot-preview";
  card.className = "iot-device-card anchor-section";

  var header = document.createElement("div");
  header.className = "iot-device-header";

  var titleWrap = document.createElement("div");
  var title = document.createElement("h2");
  title.className = "iot-device-title";
  title.textContent = "Raspberry Pi Camera Snapshot";
  var subtitle = document.createElement("p");
  subtitle.className = "iot-device-subtitle";
  subtitle.textContent = "Latest classroom snapshot uploaded from the Raspberry Pi camera.";
  titleWrap.appendChild(title);
  titleWrap.appendChild(subtitle);

  var refreshButton = document.createElement("button");
  refreshButton.type = "button";
  refreshButton.className = "iot-refresh-btn";
  refreshButton.textContent = "Refresh Snapshot";
  refreshButton.addEventListener("click", refreshIotCameraSnapshot);

  header.appendChild(titleWrap);
  header.appendChild(refreshButton);

  var grid = document.createElement("div");
  grid.className = "iot-device-grid";

  function addItem(label, valueId, valueText) {
    var item = document.createElement("div");
    item.className = "iot-device-item";
    var labelEl = document.createElement("span");
    labelEl.className = "iot-device-label";
    labelEl.textContent = label;
    var valueEl = document.createElement("span");
    valueEl.id = valueId;
    valueEl.className = "iot-device-value";
    valueEl.textContent = valueText;
    item.appendChild(labelEl);
    item.appendChild(valueEl);
    grid.appendChild(item);
  }

  addItem("Snapshot Status", "iotSnapshotStatus", "No snapshot yet");
  addItem("Uploaded At", "iotSnapshotUploadedAt", "-");
  addItem("Device", "iotSnapshotDevice", "-");
  addItem("File Size", "iotSnapshotSize", "-");

  var previewWrap = document.createElement("div");
  previewWrap.id = "iotSnapshotPreviewWrap";
  previewWrap.className = "snapshot-preview-wrap";
  previewWrap.hidden = true;

  var image = document.createElement("img");
  image.id = "iotSnapshotPreview";
  image.alt = "Latest Raspberry Pi camera snapshot";
  image.className = "snapshot-preview-image";
  previewWrap.appendChild(image);

  card.appendChild(header);
  card.appendChild(grid);
  card.appendChild(previewWrap);

  lightCards[1].insertAdjacentElement("afterend", card);
  refreshIotCameraSnapshot();
  window.setInterval(refreshIotCameraSnapshot, 10000);
});

async function refreshIotCameraSnapshot() {
  var statusEl = document.getElementById("iotSnapshotStatus");
  if (!statusEl) {
    return;
  }

  try {
    var response = await fetch("/iot/camera/latest", { cache: "no-store" });
    var data = await response.json();
    var snapshot = data.snapshot || {};
    var uploadedAtEl = document.getElementById("iotSnapshotUploadedAt");
    var deviceEl = document.getElementById("iotSnapshotDevice");
    var sizeEl = document.getElementById("iotSnapshotSize");
    var previewWrap = document.getElementById("iotSnapshotPreviewWrap");
    var image = document.getElementById("iotSnapshotPreview");

    if (!snapshot.available) {
      statusEl.textContent = "No snapshot yet";
      if (uploadedAtEl) uploadedAtEl.textContent = "-";
      if (deviceEl) deviceEl.textContent = "-";
      if (sizeEl) sizeEl.textContent = "-";
      if (previewWrap) previewWrap.hidden = true;
      return;
    }

    statusEl.textContent = "Available";
    if (uploadedAtEl) uploadedAtEl.textContent = snapshot.uploaded_at || "-";
    if (deviceEl) deviceEl.textContent = snapshot.device_name || "Raspberry Pi 5";
    if (sizeEl) {
      sizeEl.textContent = snapshot.size_bytes ? Math.round(snapshot.size_bytes / 1024) + " KB" : "-";
    }
    if (image && snapshot.url) {
      image.src = snapshot.url + "?t=" + Date.now();
    }
    if (previewWrap) previewWrap.hidden = false;
  } catch (error) {
    statusEl.textContent = "Snapshot status failed";
  }
}
