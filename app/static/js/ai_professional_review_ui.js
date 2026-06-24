(() => {
  "use strict";
  if (!location.pathname.startsWith("/ai-monitoring")) return;

  const UPLOAD_COOLDOWN_MS = 30000;
  let lastUploadAt = 0;
  let uploadRunning = false;

  const text = (id) => (document.getElementById(id)?.textContent || "").trim();
  const qs = (selector) => document.querySelector(selector);

  function getSessionId() {
    const scriptText = [...document.scripts].map((script) => script.textContent || "").join("\n");
    const match = scriptText.match(/const\s+selectedSessionId\s*=\s*"([^"]*)"/);
    return match ? match[1] : "";
  }

  function hasPhoneCandidate() {
    const value = `${text("phone-detection-status")} ${text("phone-detection-message")}`.toLowerCase();
    return value.includes("phone object candidate") || value.includes("phone-use candidate");
  }

  function hasAttentionCandidate() {
    const value = `${text("attention-detection-status")} ${text("attention-detection-message")}`.toLowerCase();
    return value.includes("attention candidate") || value.includes("looking-around candidate");
  }

  function activeReviewLabels() {
    const labels = [];
    if (hasPhoneCandidate()) labels.push("Phone-use candidate");
    if (hasAttentionCandidate()) labels.push("Looking-around candidate");
    return labels;
  }

  function simplifyCopy() {
    const replacements = [
      ["Student 1 | Attention candidate", "Student 1 Â· Looking-around candidate"],
      ["Attention candidate", "Looking-around candidate"],
      ["Phone object candidate", "Phone-use candidate"],
      ["Candidate-only result | Teacher review required", "Candidate review Â· Teacher decision required"],
      ["Demo candidate frames are based on sampled prototype status. Teacher review required.", "Candidate review frame Â· teacher decision required."],
      ["Demo candidate frame based on sampled prototype status. Teacher review required.", "Candidate review frame Â· teacher decision required."],
    ];
    document.querySelectorAll(".candidate-demo-frame-label, #current-candidate-labels, #ai-overlay-frame-status, #backend-ai-message").forEach((node) => {
      let value = node.textContent || "";
      replacements.forEach(([from, to]) => { value = value.split(from).join(to); });
      node.textContent = value;
    });
  }

  function ensureProblemStrip() {
    if (document.getElementById("professional-review-strip")) return;
    const target = document.getElementById("demo-readiness") || document.getElementById("live-camera-preview");
    if (!target) return;
    const strip = document.createElement("section");
    strip.id = "professional-review-strip";
    strip.className = "professional-review-strip";
    strip.innerHTML = `
      <article><span class="review-icon"> blind spot</strong><small>One teacher cannot watch every desk at once.</small></article>
      <article><span class="review-icon">âš‘</span><strong>Candidate highlight</strong><small>AI flags moments that may need review.</small></article>
      <article><span class="review-icon"> report</strong><small>Snapshots are saved for teacher decision.</small></article>
    `;
    target.insertAdjacentElement("beforebegin", strip);
  }

  function canvasFromVideo() {
    const video = document.getElementById("ai-video");
    const wrap = qs(".video-overlay-wrap");
    if (!video?.srcObject || !video.videoWidth || !video.videoHeight || !wrap) return null;
    const width = Math.min(1600, Math.max(960, video.videoWidth));
    const height = Math.round(width * (wrap.clientHeight / Math.max(1, wrap.clientWidth)));
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;

    const scale = Math.max(width / video.videoWidth, height / video.videoHeight);
    const cropWidth = width / scale;
    const cropHeight = height / scale;
    const sourceX = (video.videoWidth - cropWidth) / 2;
    const sourceY = (video.videoHeight - cropHeight) / 2;
    ctx.drawImage(video, sourceX, sourceY, cropWidth, cropHeight, 0, 0, width, height);

    const backendCanvas = document.getElementById("ai-overlay-canvas");
    if (backendCanvas) ctx.drawImage(backendCanvas, 0, 0, width, height);

    const labels = activeReviewLabels();
    labels.forEach((label, index) => {
      const color = label.includes("Phone") ? "#f59e0b" : "#8b5cf6";
      const x = index === 0 ? width * 0.16 : width * 0.48;
      const y = height * 0.16;
      const boxW = width * 0.46;
      const boxH = height * 0.46;
      ctx.save();
      ctx.strokeStyle = color;
      ctx.lineWidth = 6;
      ctx.shadowColor = color;
      ctx.shadowBlur = 18;
      ctx.strokeRect(x, y, boxW, boxH);
      ctx.shadowBlur = 0;
      ctx.fillStyle = color;
      ctx.fillRect(x, Math.max(0, y - 36), Math.min(boxW, 520), 36);
      ctx.fillStyle = "#fff";
      ctx.font = "700 20px system-ui, sans-serif";
      ctx.fillText(`Student ${index + 1} Â· ${label}`, x + 12, Math.max(24, y - 11));
      ctx.restore();
    });

    ctx.fillStyle = "rgba(15,23,42,.86)";
    ctx.fillRect(0, height - 74, width, 74);
    ctx.fillStyle = "#fff";
    ctx.font = "700 20px system-ui, sans-serif";
    ctx.fillText("Smart Classroom Review Evidence", 18, height - 44);
    ctx.font = "500 17px system-ui, sans-serif";
    ctx.fillText("Candidate highlight only Â· Teacher decision required", 18, height - 18);
    ctx.textAlign = "right";
    ctx.fillText(new Date().toLocaleString(), width - 18, height - 18);
    ctx.textAlign = "left";
    return canvas;
  }

  async function uploadSnapshotToReport(eventType) {
    const sessionId = getSessionId();
    const labels = activeReviewLabels();
    if (!sessionId || !labels.length || uploadRunning) return false;
    if (Date.now() - lastUploadAt < UPLOAD_COOLDOWN_MS) return false;
    const canvas = canvasFromVideo();
    if (!canvas) return false;

    uploadRunning = true;
    lastUploadAt = Date.now();
    const form = new URLSearchParams();
    form.set("session_id", sessionId);
    form.set("snapshot_data", canvas.toDataURL("image/png"));
    const endpoint = eventType === "attention" ? "/ai-monitoring/attention-event" : "/ai-monitoring/phone-event";
    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: form,
      });
      const data = await response.json().catch(() => ({}));
      const status = document.getElementById("ai-overlay-frame-status");
      if (status && response.ok) status.textContent = "Review snapshot saved to report Â· teacher decision required.";
      else if (status && data.message) status.textContent = data.message;
      return response.ok;
    } finally {
      uploadRunning = false;
    }
  }

  function autoStartReviewModes() {
    const video = document.getElementById("ai-video");
    if (!video?.srcObject) return;
    const buttons = [...document.querySelectorAll("button")];
    ["Start Advanced AI Analysis", "Start Phone Review", "Start Candidate Review"].forEach((label) => {
      const button = buttons.find((item) => item.textContent.trim() === label);
      if (button && !button.disabled) button.click();
    });
  }

  function updateStatusIcons() {
    const labels = activeReviewLabels();
    const count = document.getElementById("candidate-frames-shown");
    const current = document.getElementById("current-candidate-labels");
    if (current) {
      current.innerHTML = labels.length
        ? labels.map((label) => `<span class="review-pill">${label.includes("Phone") ? " : " ${label}</span>`).join(" ")
        : '<span class="review-pill neutral">âœ“ No candidate needing review</span>';
    }
    if (count && labels.length) count.textContent = String(Math.max(Number(count.textContent || 0), labels.length));
  }

  function loop() {
    ensureProblemStrip();
    simplifyCopy();
    updateStatusIcons();
    autoStartReviewModes();
    if (hasPhoneCandidate()) uploadSnapshotToReport("phone");
    else if (hasAttentionCandidate()) uploadSnapshotToReport("attention");
  }

  const observer = new MutationObserver(() => {
    simplifyCopy();
    updateStatusIcons();
  });
  observer.observe(document.body, { childList: true, subtree: true, characterData: true });
  setInterval(loop, 1800);
  loop();
})();
