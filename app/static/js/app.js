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
        if (typeof window.updateDemoReadinessItem === "function") {
            const checklistLabel = mode === "online"
                ? "Online"
                : mode === "fallback"
                    ? "Fallback"
                    : mode === "offline"
                        ? "Offline"
                        : "Connecting";
            const checklistMode = mode === "online"
                ? "ready"
                : mode === "fallback"
                    ? "warning"
                    : mode === "offline"
                        ? "offline"
                        : "neutral";
            window.updateDemoReadinessItem(
                "demoReadyStream",
                checklistLabel,
                checklistMode,
                message
            );
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
                setLiveStreamState("Live Stream Online", "online", "Real live stream from Raspberry Pi");
            }
        });
        liveStreamImage.addEventListener("error", () => {
            liveStreamFrameLoaded = false;
            clearLiveAiOverlay();
            if (liveStreamFallbackActive) {
                setLiveStreamState(
                    "Live Stream Offline",
                    "offline",
                    "Direct stream and snapshot fallback are unavailable."
                );
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

    function normalizedLabel(value) {
        return String(value || "").trim().toLowerCase().replace(/[-_]+/g, " ").replace(/\s+/g, " ");
    }

    function isPhoneLabel(value) {
        const label = normalizedLabel(value);
        return label.includes("phone") || label === "telephone";
    }

    function confidencePercent(value) {
        const raw = Number(value);
        if (!Number.isFinite(raw)) {
            return 0;
        }
        const percent = raw <= 1 ? raw * 100 : raw;
        return Math.max(0, Math.min(100, Math.round(percent)));
    }

    function overlayInfoForDetection(detection) {
        const label = normalizedLabel(detection.label);
        const confidence = confidencePercent(detection.confidence);
        const studentPrefix = detection.student_label || (detection.track_id ? `Student ${detection.track_id}` : "");
        let behaviorLabel = detection.behavior_label || detection.overlay_label;
        let color = detection.overlay_color;
        let risk = detection.risk || "info";

        if (!behaviorLabel) {
            if (label === "person") {
                behaviorLabel = "Person candidate";
                color = color || "#2dd4bf";
                risk = "low";
            } else if (isPhoneLabel(label)) {
                behaviorLabel = "Phone object candidate";
                color = color || "#f59e0b";
                risk = "warning";
            } else {
                behaviorLabel = detection.label ? `${detection.label} candidate` : "Object candidate";
                color = color || "#60a5fa";
            }
        }

        if (!color) {
            color = risk === "high" ? "#ef4444" : risk === "warning" ? "#f59e0b" : "#2dd4bf";
        }

        const percentText = confidence ? ` ${confidence}%` : "";
        const labelText = detection.overlay_label || `${studentPrefix ? `${studentPrefix} · ` : ""}${behaviorLabel}${percentText}`;
        return { labelText, color, risk };
    }

    function labelTextColor(backgroundColor) {
        return backgroundColor === "#f59e0b" || backgroundColor === "#2dd4bf" ? "#07131f" : "#ffffff";
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

            const overlayInfo = overlayInfoForDetection(detection);
            const color = overlayInfo.color;
            const caption = overlayInfo.labelText;

            context.strokeStyle = color;
            context.lineWidth = overlayInfo.risk === "high" ? 3.5 : 2.5;
            context.strokeRect(left, top, width, height);
            context.font = "800 13px Segoe UI, Arial, sans-serif";
            const labelWidth = Math.min(context.measureText(caption).width + 14, displayWidth - left - 4);
            const labelHeight = 24;
            const labelTop = top >= labelHeight ? top - labelHeight : top;
            context.fillStyle = color;
            context.fillRect(left, labelTop, labelWidth, labelHeight);
            context.fillStyle = labelTextColor(color);
            context.fillText(caption, left + 7, labelTop + 16);
        });
    }

    function behaviorCountsLabel(analysis, detections) {
        const summary = analysis.behavior_summary || {};
        const counts = summary.counts || {};
        const phoneUsage = Number(counts.possible_phone_usage || 0);
        const phoneObjects = Number(counts.phone_object || 0);
        if (phoneUsage > 0) {
            return `${phoneUsage} phone-use candidate${phoneUsage === 1 ? "" : "s"} for review`;
        }
        if (phoneObjects > 0) {
            return `${phoneObjects} phone object candidate${phoneObjects === 1 ? "" : "s"} for review`;
        }
        return `${detections.length} sampled object candidate${detections.length === 1 ? "" : "s"}`;
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
                `${detections.length ? behaviorCountsLabel(analysis, detections) : "No behavior objects"} · ${ageLabel}`
            );
        } else if (!detections.length) {
            setLiveAiStatus(
                "No AI objects detected yet.",
                "",
                `Latest sampled analysis · ${ageLabel}`
            );
        } else {
            setLiveAiStatus(
                behaviorCountsLabel(analysis, detections),
                "",
                `Behavior labels use the latest sampled analysis · ${ageLabel}`
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
