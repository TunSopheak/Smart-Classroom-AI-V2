document.addEventListener("DOMContentLoaded", () => {
    const menus = Array.from(document.querySelectorAll(".nav-menu"));

    function closeMenus(except = null) {
        menus.forEach((menu) => {
            if (menu !== except) {
                menu.removeAttribute("open");
            }
        });
    }

    menus.forEach((menu) => {
        const summary = menu.querySelector("summary");
        const links = menu.querySelectorAll("a");

        summary?.addEventListener("click", () => {
            requestAnimationFrame(() => {
                if (menu.open) {
                    closeMenus(menu);
                }
            });
        });

        links.forEach((link) => {
            link.addEventListener("click", () => closeMenus());
        });
    });

    document.addEventListener("click", (event) => {
        if (!event.target.closest(".nav-menu")) {
            closeMenus();
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeMenus();
        }
    });

    document.querySelectorAll(".notice").forEach((notice) => {
        window.setTimeout(() => {
            notice.classList.add("is-dismissing");
            window.setTimeout(() => notice.remove(), 450);
        }, 5200);
    });
});
