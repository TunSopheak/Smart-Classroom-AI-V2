(() => {
  "use strict";

  if (!location.pathname.startsWith("/ai-monitoring")) return;

  const COLORS = {
    person: "#14b8a6",
    attention: "#8b5cf6",
    phone: "#f59e0b",
    leaning: "#f97316",
  };
  const WATCHED_IDS = [
    "phone-detection-status",
    "phone-detection-message",
    "phone-confidence",
    "attention-detection-status",
    "attention-detection-message",
    "attention-confidence",
    "ai-overlay-canvas",
  ];
  const autoSnapshotCooldownMs = 30000;
  let lastAutoSnapshotAt = 0;
  let lastAutoSnapshotReason = "";
  let autoSnapshotInFlight = false;
  let lastSnapshotMessageAt = 0;

  const getText = (id) =>
    (document.getElementById(id)?.textContent || "").trim();
  const confidencePercent = (id) =>
    (getText(id).match(/(\d+)%/) || [])[1] || null;
  const labelWithConfidence = (label, confidence) =>
    confidence ? `${label} ${confidence}%` : label;

  function hasPhoneCandidate() {
    const status = getText("phone-detection-status").toLowerCase();
    return status === "phone object candidate" || status === "phone-use candidate";
  }

  function hasAttentionCandidate() {
    return getText("attention-detection-status").toLowerCase() === "attention candidate";
  }

  function getBackendFrameCount() {
    const canvas = document.getElementById("ai-overlay-canvas");
    const count = Number(canvas?.dataset.frameCount || 0);
    return Number.isFinite(count) ? count : 0;
  }

  function getBackendCandidateLabels() {
    const raw = document.getElementById("ai-overlay-canvas")?.dataset
      .candidateLabels;
    if (!raw) return [];
    try {
      const labels = JSON.parse(raw);
      return Array.isArray(labels)
        ? labels.filter((label) => typeof label === "string" && label.trim())
        : [];
    } catch (_error) {
      return [];
    }
  }

  function backendHasCandidateType(candidateType) {
    const needle = candidateType.toLowerCase();
    return getBackendCandidateLabels().some((label) =>
      label.toLowerCase().includes(needle),
    );
  }

  function getActiveCandidateFrames() {
    const video = document.getElementById("ai-video");
    if (!video?.srcObject) return [];

    const frames = [];
    if (
      hasAttentionCandidate() &&
      !backendHasCandidateType("attention") &&
      !backendHasCandidateType("looking-around")
    ) {
      frames.push({
        label: labelWithConfidence(
          "Student 1 | Attention candidate",
          confidencePercent("attention-confidence"),
        ),
        color: COLORS.attention,
        x: 0.2,
        y: 0.12,
        width: 0.54,
        height: 0.58,
        source: "sampled prototype status",
      });
    }
    if (hasPhoneCandidate() && !backendHasCandidateType("phone")) {
      frames.push({
        label: labelWithConfidence(
          "Student 1 | Phone-use candidate",
          confidencePercent("phone-confidence"),
        ),
        color: COLORS.phone,
        x: 0.58,
        y: 0.42,
        width: 0.34,
        height: 0.48,
        source: "sampled prototype status",
      });
    }
    return frames;
  }

  function getOverlayLayer() {
    const wrap = document.querySelector(".video-overlay-wrap");
    if (!wrap) return null;
    let node = wrap.querySelector(".candidate-demo-overlay-layer");
    if (!node) {
      node = document.createElement("div");
      node.className = "candidate-demo-overlay-layer";
      node.setAttribute("aria-hidden", "true");
      wrap.appendChild(node);
    }
    return node;
  }

  function drawCandidateFrame(frame) {
    const node = document.createElement("div");
    node.className = "candidate-demo-frame";
    node.dataset.candidateLabel = frame.label;
    node.style.setProperty("--candidate-color", frame.color);
    Object.assign(node.style, {
      left: `${frame.x * 100}%`,
      top: `${frame.y * 100}%`,
      width: `${frame.width * 100}%`,
      height: `${frame.height * 100}%`,
    });

    const label = document.createElement("div");
    label.className = "candidate-demo-frame-label";
    label.textContent = frame.label;
    node.appendChild(label);
    return node;
  }

  function updateStatusPanel(fallbackFrames) {
    const backendCount = getBackendFrameCount();
    const frameCount = backendCount + fallbackFrames.length;
    const labels = [
      ...getBackendCandidateLabels(),
      ...fallbackFrames.map((frame) => frame.label),
    ].filter((label, index, all) => all.indexOf(label) === index);
    const countNode = document.getElementById("candidate-frames-shown");
    const labelsNode = document.getElementById("current-candidate-labels");
    const captureButton = document.getElementById("capture-review-snapshot");
    const video = document.getElementById("ai-video");

    if (countNode) countNode.textContent = String(frameCount);
    if (labelsNode) {
      labelsNode.textContent = labels.length
        ? labels.join(" · ")
        : "No active candidate labels";
    }
    if (captureButton) captureButton.disabled = !video?.srcObject;
  }

  function renderCandidateOverlay() {
    const target = getOverlayLayer();
    if (!target) return;

    const frames = getActiveCandidateFrames();
    const signature = JSON.stringify(frames);
    if (target.dataset.signature !== signature) {
      target.dataset.signature = signature;
      target.replaceChildren(...frames.map(drawCandidateFrame));
    }

    const status = document.getElementById("ai-overlay-frame-status");
    if (
      status &&
      frames.length &&
      Date.now() - lastSnapshotMessageAt > 4000
    ) {
      status.textContent =
        "Demo candidate frames are based on sampled prototype status. Teacher review required.";
    }
    updateStatusPanel(frames);
    autoCaptureSnapshotForCandidate("phone-use candidate");
  }

  function drawVideoCover(context, video, width, height) {
    const sourceWidth = video.videoWidth;
    const sourceHeight = video.videoHeight;
    const scale = Math.max(width / sourceWidth, height / sourceHeight);
    const cropWidth = width / scale;
    const cropHeight = height / scale;
    const sourceX = (sourceWidth - cropWidth) / 2;
    const sourceY = (sourceHeight - cropHeight) / 2;
    context.drawImage(
      video,
      sourceX,
      sourceY,
      cropWidth,
      cropHeight,
      0,
      0,
      width,
      height,
    );
  }

  function drawSnapshotCandidateFrame(context, frame, width, height) {
    const x = frame.x * width;
    const y = frame.y * height;
    const boxWidth = frame.width * width;
    const boxHeight = frame.height * height;
    const lineWidth = Math.max(4, Math.round(width / 320));
    const fontSize = Math.max(16, Math.round(width / 55));
    const paddingX = Math.max(8, Math.round(fontSize * 0.55));
    const labelHeight = Math.round(fontSize * 1.65);

    context.lineWidth = lineWidth;
    context.strokeStyle = frame.color;
    context.shadowColor = frame.color;
    context.shadowBlur = Math.max(8, lineWidth * 3);
    context.strokeRect(x, y, boxWidth, boxHeight);
    context.shadowBlur = 0;
    const corner = Math.max(18, Math.min(34, boxWidth / 4, boxHeight / 4));
    context.beginPath();
    context.lineWidth = lineWidth * 1.75;
    context.moveTo(x, y + corner);
    context.lineTo(x, y);
    context.lineTo(x + corner, y);
    context.moveTo(x + boxWidth - corner, y);
    context.lineTo(x + boxWidth, y);
    context.lineTo(x + boxWidth, y + corner);
    context.moveTo(x, y + boxHeight - corner);
    context.lineTo(x, y + boxHeight);
    context.lineTo(x + corner, y + boxHeight);
    context.moveTo(x + boxWidth - corner, y + boxHeight);
    context.lineTo(x + boxWidth, y + boxHeight);
    context.lineTo(x + boxWidth, y + boxHeight - corner);
    context.stroke();
    context.font = `700 ${fontSize}px system-ui, sans-serif`;
    const labelWidth = Math.min(
      width - x,
      context.measureText(frame.label).width + paddingX * 2,
    );
    const labelY = Math.max(0, y - labelHeight);
    context.fillStyle = frame.color;
    context.fillRect(x, labelY, labelWidth, labelHeight);
    context.fillStyle = "#ffffff";
    context.fillText(frame.label, x + paddingX, labelY + fontSize + 4);
  }

  function drawSnapshotFooter(context, width, height) {
    const fontSize = Math.max(15, Math.round(width / 64));
    const padding = Math.max(12, Math.round(width / 80));
    const panelHeight = fontSize * 3.6;
    context.fillStyle = "rgba(15, 23, 42, 0.86)";
    context.fillRect(0, height - panelHeight, width, panelHeight);
    context.fillStyle = "#ffffff";
    context.font = `700 ${fontSize}px system-ui, sans-serif`;
    context.fillText(
      "Smart Classroom AI Review Snapshot",
      padding,
      height - panelHeight + fontSize + padding / 2,
    );
    context.font = `500 ${fontSize}px system-ui, sans-serif`;
    context.fillText(
      "Candidate-only result | Teacher review required",
      padding,
      height - padding,
    );
    context.textAlign = "right";
    context.fillText(new Date().toLocaleString(), width - padding, height - padding);
    context.textAlign = "left";
  }

  function snapshotFilename(date = new Date()) {
    const part = (value) => String(value).padStart(2, "0");
    return `smart-classroom-review-snapshot-${date.getFullYear()}${part(
      date.getMonth() + 1,
    )}${part(date.getDate())}-${part(date.getHours())}${part(
      date.getMinutes(),
    )}${part(date.getSeconds())}.png`;
  }

  function downloadSnapshotPng(canvas, filename) {
    return new Promise((resolve, reject) => {
      canvas.toBlob((blob) => {
        if (!blob) {
          reject(new Error("Snapshot PNG could not be created."));
          return;
        }
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
        resolve();
      }, "image/png");
    });
  }

  async function captureReviewSnapshot(options = {}) {
    const video = document.getElementById("ai-video");
    const wrap = document.querySelector(".video-overlay-wrap");
    const status = document.getElementById("ai-overlay-frame-status");
    if (!video?.srcObject || !video.videoWidth || !video.videoHeight || !wrap) {
      if (status) status.textContent = "Start the computer camera before capturing a review snapshot.";
      return false;
    }

    const aspectRatio = wrap.clientWidth / Math.max(1, wrap.clientHeight);
    const width = Math.min(1920, Math.max(960, video.videoWidth));
    const height = Math.round(width / aspectRatio);
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext("2d");
    if (!context) return false;

    drawVideoCover(context, video, width, height);
    const backendCanvas = document.getElementById("ai-overlay-canvas");
    if (backendCanvas && getBackendFrameCount() > 0) {
      context.drawImage(backendCanvas, 0, 0, width, height);
    }
    getActiveCandidateFrames().forEach((frame) =>
      drawSnapshotCandidateFrame(context, frame, width, height),
    );
    drawSnapshotFooter(context, width, height);

    await downloadSnapshotPng(canvas, snapshotFilename());
    const capturedAt = new Date();
    const lastSnapshot = document.getElementById("last-review-snapshot");
    if (lastSnapshot) lastSnapshot.textContent = capturedAt.toLocaleTimeString();
    lastSnapshotMessageAt = capturedAt.getTime();
    if (status) {
      status.textContent =
        options.statusMessage ||
        "Review snapshot captured. Candidate labels require teacher review.";
    }
    return true;
  }

  function shouldAutoCaptureSnapshot(candidateType) {
    if (candidateType.toLowerCase() !== "phone-use candidate") return false;
    const video = document.getElementById("ai-video");
    if (!video?.srcObject || autoSnapshotInFlight) return false;
    if (Date.now() - lastAutoSnapshotAt < autoSnapshotCooldownMs) return false;

    const fallbackFrames = getActiveCandidateFrames();
    const phoneFrameVisible =
      backendHasCandidateType("phone") ||
      fallbackFrames.some((frame) =>
        frame.label.toLowerCase().includes("phone-use candidate"),
      );
    const visibleFrameCount = getBackendFrameCount() + fallbackFrames.length;
    const phoneCandidateActive = hasPhoneCandidate() || backendHasCandidateType("phone");
    return phoneCandidateActive && phoneFrameVisible && visibleFrameCount > 0;
  }

  function autoCaptureSnapshotForCandidate(reason) {
    if (!shouldAutoCaptureSnapshot(reason)) return false;

    autoSnapshotInFlight = true;
    lastAutoSnapshotAt = Date.now();
    lastAutoSnapshotReason = reason;
    captureReviewSnapshot({
      statusMessage:
        "Phone-use candidate snapshot captured for teacher review.",
    })
      .catch(() => {
        const status = document.getElementById("ai-overlay-frame-status");
        if (status) {
          status.textContent =
            "Automatic snapshot download may be blocked. Manual Capture Review Snapshot remains available.";
        }
      })
      .finally(() => {
        autoSnapshotInFlight = false;
      });
    return true;
  }

  function start() {
    const observer = new MutationObserver(renderCandidateOverlay);
    WATCHED_IDS.forEach((id) => {
      const node = document.getElementById(id);
      if (node) {
        observer.observe(node, {
          childList: true,
          subtree: true,
          characterData: true,
          attributes: true,
        });
      }
    });

    const video = document.getElementById("ai-video");
    video?.addEventListener("loadedmetadata", renderCandidateOverlay);
    video?.addEventListener("play", renderCandidateOverlay);
    document
      .getElementById("capture-review-snapshot")
      ?.addEventListener("click", () => {
        captureReviewSnapshot().catch(() => {
          const status = document.getElementById("ai-overlay-frame-status");
          if (status) {
            status.textContent =
              "Review snapshot could not be captured. Please try the sampled frame again.";
          }
        });
      });
    addEventListener("resize", renderCandidateOverlay);
    setInterval(renderCandidateOverlay, 500);
    renderCandidateOverlay();
  }

  window.smartClassroomDemoOverlay = {
    autoCaptureSnapshotForCandidate,
    captureReviewSnapshot,
    downloadSnapshotPng,
    drawCandidateFrame,
    getActiveCandidateFrames,
    renderCandidateOverlay,
    shouldAutoCaptureSnapshot,
    getAutoSnapshotState: () => ({
      autoSnapshotCooldownMs,
      lastAutoSnapshotAt,
      lastAutoSnapshotReason,
    }),
  };

  document.readyState === "loading"
    ? document.addEventListener("DOMContentLoaded", start)
    : start();
})();
/* Friendly real-world demo patch: auto-start review and teacher-support wording */
(() => {
  if (!location.pathname.startsWith("/ai-monitoring")) return;

  const friendlyLabel = (text) => {
    return String(text || "")
      .replace("Student 1 | Attention candidate", "Student 1 | Review needed · Looking-around candidate")
      .replace("Attention candidate", "Looking-around candidate")
      .replace("Phone object candidate", "Phone-use candidate")
      .replace("Phone-use candidate", "Phone-use candidate");
  };

  function patchVisibleLabels() {
    document.querySelectorAll(".candidate-demo-frame-label").forEach((node) => {
      node.textContent = friendlyLabel(node.textContent);
    });

    const currentLabels = document.getElementById("current-candidate-labels");
    if (currentLabels && currentLabels.textContent) {
      currentLabels.textContent = friendlyLabel(currentLabels.textContent);
    }

    const status = document.getElementById("ai-overlay-frame-status");
    if (status && status.textContent.includes("Demo candidate")) {
      status.textContent =
        "AI highlights possible classroom review points. Candidate-only result; teacher review required.";
    }
  }

  function ensureTeacherSupportPanel() {
    const cameraSection = document.querySelector("#classroom-status") || document.querySelector(".monitor-section");
    if (!cameraSection || document.getElementById("teacher-review-support-panel")) return;

    const panel = document.createElement("div");
    panel.id = "teacher-review-support-panel";
    panel.className = "helper-note";
    panel.style.marginTop = "12px";
    panel.innerHTML = `
      <strong>Teacher Review Support</strong>
      <span>
        Real-world problem: a teacher cannot watch every student at the same time.
        This system highlights possible review points such as phone-use candidate or looking-around candidate.
        It does not make final judgments.
      </span>
    `;
    cameraSection.prepend(panel);
  }

  function safeClick(button) {
    if (button && !button.disabled) {
      button.click();
      return true;
    }
    return false;
  }

  function autoStartReviewLoop() {
    const video = document.getElementById("ai-video");
    if (!video || !video.srcObject) return;

    let tries = 0;
    const timer = setInterval(() => {
      tries += 1;

      const startAdvanced = [...document.querySelectorAll("button")]
        .find((btn) => btn.textContent.trim() === "Start Advanced AI Analysis");
      const startPhone = document.getElementById("start-phone-detection") ||
        [...document.querySelectorAll("button")].find((btn) => btn.textContent.trim() === "Start Phone Review");
      const startAttention = document.getElementById("start-attention-detection") ||
        [...document.querySelectorAll("button")].find((btn) => btn.textContent.trim() === "Start Candidate Review");

      safeClick(startAdvanced);
      safeClick(startPhone);
      safeClick(startAttention);

      const cameraStatus = document.getElementById("camera-status");
      if (cameraStatus) {
        cameraStatus.textContent =
          "Camera ready. Safe AI review is starting automatically. Manual retry is available.";
      }

      if (tries >= 12) clearInterval(timer);
    }, 1000);
  }

  function bootFriendlyDemoPatch() {
    ensureTeacherSupportPanel();

    const startCameraButton = [...document.querySelectorAll("button")]
      .find((btn) => btn.textContent.trim() === "Start Camera");

    if (startCameraButton && !startCameraButton.dataset.friendlyAutoStartBound) {
      startCameraButton.dataset.friendlyAutoStartBound = "1";
      startCameraButton.addEventListener("click", () => {
        setTimeout(autoStartReviewLoop, 1200);
      });
    }

    setInterval(() => {
      patchVisibleLabels();
      ensureTeacherSupportPanel();

      const video = document.getElementById("ai-video");
      if (video && video.srcObject) {
        autoStartReviewLoop();
      }
    }, 3500);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootFriendlyDemoPatch);
  } else {
    bootFriendlyDemoPatch();
  }
})();
