(() => {
  "use strict";

  if (!location.pathname.startsWith("/ai-monitoring")) return;

  const getText = (id) =>
    (document.getElementById(id)?.textContent || "").trim();
  const hasPhone = () => {
    const status = getText("phone-detection-status").toLowerCase();
    return status === "phone object candidate" || status === "phone-use candidate";
  };
  const hasAttention = () => {
    const status = getText("attention-detection-status").toLowerCase();
    return status === "attention candidate";
  };
  const pct = (id) => (getText(id).match(/(\d+)%/) || [])[1];
  const labelWithConfidence = (label, confidence) =>
    confidence ? `${label} ${confidence}%` : label;

  function layer() {
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

  function box(label, color, style) {
    const node = document.createElement("div");
    Object.assign(node.style, {
      position: "absolute",
      border: `4px solid ${color}`,
      borderRadius: "14px",
      boxShadow:
        "0 0 0 2px rgba(255,255,255,.9), 0 8px 24px rgba(0,0,0,.2)",
      ...style,
    });
    const tag = document.createElement("div");
    tag.textContent = label;
    Object.assign(tag.style, {
      position: "absolute",
      left: "0",
      top: "-32px",
      padding: "5px 9px",
      color: "#fff",
      background: color,
      borderRadius: "9px",
      fontWeight: "800",
      fontSize: "13px",
      whiteSpace: "nowrap",
    });
    node.appendChild(tag);
    return node;
  }

  function draw() {
    const target = layer();
    const video = document.getElementById("ai-video");
    if (!target || !video) return;
    const frames = [];
    if (video.srcObject && hasAttention()) {
      frames.push(
        box(
          labelWithConfidence(
            "Attention candidate",
            pct("attention-confidence"),
          ),
          "#8b5cf6",
          { left: "20%", top: "10%", width: "54%", height: "58%" },
        ),
      );
    }
    if (video.srcObject && hasPhone()) {
      frames.push(
        box(
          labelWithConfidence("Phone-use candidate", pct("phone-confidence")),
          "#f59e0b",
          { right: "8%", top: "38%", width: "34%", height: "50%" },
        ),
      );
    }
    const signature = frames.map((frame) => frame.textContent).join("|");
    if (target.dataset.signature !== signature) {
      target.dataset.signature = signature;
      target.replaceChildren(...frames);
    }
    const status = document.getElementById("ai-overlay-frame-status");
    if (status && frames.length) {
      status.textContent = `${frames.length} candidate review frame${frames.length === 1 ? "" : "s"} shown. Teacher review required.`;
    }
  }

  const start = () => {
    const watchedIds = [
      "phone-detection-status",
      "phone-detection-message",
      "phone-confidence",
      "attention-detection-status",
      "attention-detection-message",
      "attention-confidence",
    ];
    const observer = new MutationObserver(draw);
    watchedIds.forEach((id) => {
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
    video?.addEventListener("loadedmetadata", draw);
    video?.addEventListener("play", draw);
    addEventListener("resize", draw);
    setInterval(draw, 500);
    draw();
  };
  document.readyState === "loading"
    ? document.addEventListener("DOMContentLoaded", start)
    : start();
})();
