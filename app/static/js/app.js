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
    let liveStreamFallbackActive = false;
    let liveStreamTimeout = null;

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
        window.clearTimeout(liveStreamTimeout);
        setLiveStreamState("Connecting", "", "Connecting to Raspberry Pi live stream...");
        liveStreamImage.src = `${liveStreamImage.dataset.directSrc}${liveStreamImage.dataset.directSrc.includes("?") ? "&" : "?"}t=${Date.now()}`;
        liveStreamImage.alt = "Real live stream from Raspberry Pi camera";
        liveStreamTimeout = window.setTimeout(useSnapshotFallback, 6000);
    }

    if (liveStreamImage) {
        liveStreamImage.addEventListener("load", () => {
            window.clearTimeout(liveStreamTimeout);
            if (!liveStreamFallbackActive) {
                setLiveStreamState("Live from Pi", "online", "Real live stream from Raspberry Pi");
            }
        });
        liveStreamImage.addEventListener("error", () => {
            if (liveStreamFallbackActive) {
                return;
            }
            useSnapshotFallback();
        });
        retryLiveStreamButton?.addEventListener("click", loadDirectPiStream);
        loadDirectPiStream();
    }
});
