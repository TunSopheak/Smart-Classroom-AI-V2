document.addEventListener("DOMContentLoaded", () => {
    const menuToggle = document.querySelector(".menu-toggle");
    const sidebarClose = document.querySelector(".sidebar-close");
    const sidebar = document.querySelector(".sidebar");
    const sidebarBackdrop = document.querySelector(".sidebar-backdrop");

    function openSidebar() {
        sidebar?.classList.add("is-open");
        sidebarBackdrop?.classList.add("is-open");
        document.body.classList.add("nav-open");
        menuToggle?.setAttribute("aria-expanded", "true");
    }

    function closeSidebar() {
        sidebar?.classList.remove("is-open");
        sidebarBackdrop?.classList.remove("is-open");
        document.body.classList.remove("nav-open");
        menuToggle?.setAttribute("aria-expanded", "false");
    }

    menuToggle?.addEventListener("click", () => {
        if (sidebar?.classList.contains("is-open")) {
            closeSidebar();
        } else {
            openSidebar();
        }
    });
    sidebarClose?.addEventListener("click", closeSidebar);
    sidebarBackdrop?.addEventListener("click", closeSidebar);
    sidebar?.querySelectorAll(".nav-group-link, .nav-sub-link").forEach((link) => link.addEventListener("click", closeSidebar));

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeSidebar();
        }
    });

    document.querySelectorAll(".notice").forEach((notice) => {
        window.setTimeout(() => {
            notice.classList.add("is-dismissing");
            window.setTimeout(() => notice.remove(), 450);
        }, 5200);
    });

    const liveStreamImage = document.getElementById("pi-live-stream");
    const liveStreamBadge = document.getElementById("pi-live-stream-badge");
    const liveStreamMessage = document.getElementById("pi-live-stream-message");
    const retryLiveStreamButton = document.getElementById("retry-pi-live-stream");
    const liveAiOverlay = document.getElementById("pi-live-ai-overlay");
    const liveAiStatus = document.getElementById("live-ai-overlay-status");
    const liveAiDetail = document.getElementById("live-ai-overlay-detail");
    let liveStreamFallbackActive = false;
    let liveStreamFrameLoaded = false;
    let liveStreamTimeout = null;
    let latestOverlayState = null;

    function setLiveStreamState(label, mode, message) {
        if (liveStreamBadge) {
            liveStreamBadge.textContent = label;
            liveStreamBadge.classList.toggle("online", mode === "online");
            liveStreamBadge.classList.toggle("fallback", mode === "fallback");
            liveStreamBadge.classList.toggle("offline", mode === "offline");
        }
        if (liveStreamMessage) {
            liveStreamMessage.textContent = message;
        }
    }

    function useSnapshotFallback() {
        if (!liveStreamImage || liveStreamFallbackActive) {
            return;
        }
        liveStreamFallbackActive = true;
        liveStreamFrameLoaded = false;
        window.clearTimeout(liveStreamTimeout);
        setLiveStreamState("Snapshot fallback", "fallback", "Waiting for Raspberry Pi frame...");
        liveStreamImage.src = `${liveStreamImage.dataset.fallbackSrc}?t=${Date.now()}`;
        liveStreamImage.alt = "Fallback preview using the latest uploaded Raspberry Pi frame";
    }

    function loadDirectPiStream() {
        if (!liveStreamImage) {
            return;
        }
        liveStreamFallbackActive = false;
        liveStreamFrameLoaded = false;
        window.clearTimeout(liveStreamTimeout);
        setLiveStreamState("Connecting", "", "Connecting to Raspberry Pi live stream...");
        liveStreamImage.src = `${liveStreamImage.dataset.directSrc}${liveStreamImage.dataset.directSrc.includes("?") ? "&" : "?"}t=${Date.now()}`;
        liveStreamImage.alt = "Real live stream from Raspberry Pi camera";
        liveStreamTimeout = window.setTimeout(useSnapshotFallback, 6000);
    }

    if (liveStreamImage) {
        liveStreamImage.addEventListener("load", () => {
            window.clearTimeout(liveStreamTimeout);
            liveStreamFrameLoaded = true;
            drawLiveAiOverlay(latestOverlayState);
            if (!liveStreamFallbackActive) {
                setLiveStreamState("Live from Pi", "online", "Real live stream from Raspberry Pi");
            }
        });
        liveStreamImage.addEventListener("error", () => {
            liveStreamFrameLoaded = false;
            clearLiveAiOverlay();
            if (liveStreamFallbackActive) {
                return;
            }
            useSnapshotFallback();
        });
        retryLiveStreamButton?.addEventListener("click", loadDirectPiStream);
        loadDirectPiStream();
    }

    function setLiveAiStatus(message, mode, detail) {
        if (liveAiStatus) {
            liveAiStatus.textContent = message;
            liveAiStatus.classList.toggle("waiting", mode === "waiting");
            liveAiStatus.classList.toggle("stale", mode === "stale");
            liveAiStatus.classList.toggle("unavailable", mode === "unavailable");
        }
        if (liveAiDetail) {
            liveAiDetail.textContent = detail;
        }
    }

    function analysisAgeSeconds(timestamp) {
        if (!timestamp) {
            return null;
        }
        let normalized = String(timestamp).trim();
        if (!/[zZ]$|[+-]\d{2}:?\d{2}$/.test(normalized)) {
            normalized = `${normalized.replace(" ", "T")}Z`;
        }
        const analyzedAt = new Date(normalized);
        if (Number.isNaN(analyzedAt.getTime())) {
            return null;
        }
        return Math.max(0, Math.round((Date.now() - analyzedAt.getTime()) / 1000));
    }

    function clearLiveAiOverlay() {
        if (!liveAiOverlay) {
            return;
        }
        const context = liveAiOverlay.getContext("2d");
        context?.clearRect(0, 0, liveAiOverlay.width, liveAiOverlay.height);
    }

    function drawLiveAiOverlay(state) {
        if (!liveAiOverlay || !state || !liveStreamFrameLoaded) {
            clearLiveAiOverlay();
            return;
        }
        const analysis = state.analysis || {};
        const sourceWidth = Number(analysis.image_width);
        const sourceHeight = Number(analysis.image_height);
        const detections = Array.isArray(analysis.detections) ? analysis.detections : [];
        const displayWidth = liveAiOverlay.clientWidth;
        const displayHeight = liveAiOverlay.clientHeight;
        if (!displayWidth || !displayHeight || !sourceWidth || !sourceHeight) {
            clearLiveAiOverlay();
            return;
        }

        const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
        liveAiOverlay.width = Math.round(displayWidth * pixelRatio);
        liveAiOverlay.height = Math.round(displayHeight * pixelRatio);
        const context = liveAiOverlay.getContext("2d");
        if (!context) {
            return;
        }
        context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
        context.clearRect(0, 0, displayWidth, displayHeight);

        const scale = Math.min(displayWidth / sourceWidth, displayHeight / sourceHeight);
        const renderedWidth = sourceWidth * scale;
        const renderedHeight = sourceHeight * scale;
        const offsetX = (displayWidth - renderedWidth) / 2;
        const offsetY = (displayHeight - renderedHeight) / 2;

        detections.forEach((detection) => {
            if (!Array.isArray(detection.box) || detection.box.length !== 4) {
                return;
            }
            const coordinates = detection.box.map(Number);
            if (!coordinates.every(Number.isFinite)) {
                return;
            }
            const [x1, y1, x2, y2] = coordinates;
            const left = offsetX + Math.max(0, Math.min(sourceWidth, x1)) * scale;
            const top = offsetY + Math.max(0, Math.min(sourceHeight, y1)) * scale;
            const right = offsetX + Math.max(0, Math.min(sourceWidth, x2)) * scale;
            const bottom = offsetY + Math.max(0, Math.min(sourceHeight, y2)) * scale;
            const width = Math.max(0, right - left);
            const height = Math.max(0, bottom - top);
            if (width < 2 || height < 2) {
                return;
            }

            const label = String(detection.label || "object");
            const rawConfidence = Number(detection.confidence);
            const confidence = Number.isFinite(rawConfidence)
                ? Math.round((rawConfidence <= 1 ? rawConfidence * 100 : rawConfidence))
                : 0;
            const caption = `${label} ${Math.max(0, Math.min(100, confidence))}%`;
            const color = label.toLowerCase().includes("phone") ? "#f59e0b" : "#2dd4bf";

            context.strokeStyle = color;
            context.lineWidth = 2.5;
            context.strokeRect(left, top, width, height);
            context.font = "700 13px Segoe UI, Arial, sans-serif";
            const labelWidth = context.measureText(caption).width + 12;
            const labelHeight = 23;
            const labelTop = top >= labelHeight ? top - labelHeight : top;
            context.fillStyle = color;
            context.fillRect(left, labelTop, labelWidth, labelHeight);
            context.fillStyle = "#07131f";
            context.fillText(caption, left + 6, labelTop + 16);
        });
    }

    function renderLiveAiState(state) {
        latestOverlayState = state;
        if (!state || !state.available || !state.analysis) {
            clearLiveAiOverlay();
            setLiveAiStatus(
                "Waiting for AI sample...",
                "waiting",
                "Detection boxes will appear after the backend analyzes its first sampled snapshot."
            );
            return;
        }

        const analysis = state.analysis;
        if (analysis.available === false) {
            clearLiveAiOverlay();
            setLiveAiStatus(
                "AI sample unavailable",
                "unavailable",
                analysis.message || "The latest sample could not be analyzed."
            );
            return;
        }

        drawLiveAiOverlay(state);
        const detections = Array.isArray(analysis.detections) ? analysis.detections : [];
        const age = analysisAgeSeconds(state.analyzed_at);
        const ageLabel = age === null ? "age unavailable" : `${age}s old`;
        if (age !== null && age > 20) {
            setLiveAiStatus(
                "Using latest AI sample.",
                "stale",
                `${detections.length ? `${detections.length} object${detections.length === 1 ? "" : "s"}` : "No objects"} in the latest sample · ${ageLabel}`
            );
        } else if (!detections.length) {
            setLiveAiStatus(
                "No AI objects detected yet.",
                "",
                `Latest sampled analysis · ${ageLabel}`
            );
        } else {
            setLiveAiStatus(
                `${detections.length} AI object${detections.length === 1 ? "" : "s"} detected`,
                "",
                `Boxes use the latest sampled analysis · ${ageLabel}`
            );
        }
    }

    async function pollLiveAiOverlay() {
        if (!liveAiOverlay) {
            return;
        }
        try {
            const response = await fetch("/iot/camera/latest", { cache: "no-store" });
            if (!response.ok) {
                throw new Error(`AI sample status returned ${response.status}`);
            }
            const data = await response.json();
            renderLiveAiState(data.analysis_state);
        } catch (error) {
            if (latestOverlayState) {
                drawLiveAiOverlay(latestOverlayState);
                setLiveAiStatus(
                    "Using latest AI sample.",
                    "stale",
                    "AI status refresh is temporarily unavailable; retaining the last sampled result."
                );
            } else {
                clearLiveAiOverlay();
                setLiveAiStatus(
                    "AI sample status unavailable",
                    "unavailable",
                    "The live video can continue while the backend sample status reconnects."
                );
            }
        }
    }

    if (liveAiOverlay) {
        pollLiveAiOverlay();
        window.setInterval(pollLiveAiOverlay, 2500);
        if (window.ResizeObserver) {
            const overlayResizeObserver = new ResizeObserver(() => drawLiveAiOverlay(latestOverlayState));
            overlayResizeObserver.observe(liveAiOverlay);
        } else {
            window.addEventListener("resize", () => drawLiveAiOverlay(latestOverlayState));
        }
    }
});
