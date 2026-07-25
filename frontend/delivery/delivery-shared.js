/**
 * SYRA Fresh - Delivery Portal Shared JS
 * Handles auth checks, nav, toasts, and API calls for the delivery portal.
 */

const DELIVERY_API = "http://localhost:5000/api/delivery";

/* ───── Theme ─────
 * BUG FIX: dark mode used to only be applied by settings.html itself (it
 * read+set localStorage("theme") and set data-theme only on that one page).
 * Every other delivery page never checked it, so turning on dark mode in
 * Settings would silently revert back to light the moment you navigated
 * anywhere else. Applying it here - loaded by every delivery page - fixes
 * that, and switches to the same "syra_theme" key the storefront and
 * admin/hub-manager panels already use, so the preference is consistent
 * site-wide instead of a delivery-panel-only value. */
document.documentElement.setAttribute("data-theme", localStorage.getItem("syra_theme") || "light");

/* ───── Auth ───── */
function getDeliveryToken() {
    return localStorage.getItem("delivery_token");
}

function getDeliveryUser() {
    try {
        return JSON.parse(localStorage.getItem("delivery_user") || "{}");
    } catch { return {}; }
}

function requireDeliveryAuth() {
    if (!getDeliveryToken()) {
        window.location.href = "login.html";
        return false;
    }
    return true;
}

function deliveryLogout() {
    if (confirm("Are you sure you want to logout?")) {
        localStorage.removeItem("delivery_token");
        localStorage.removeItem("delivery_user");
        localStorage.removeItem("role");
        window.location.href = "login.html";
    }
}

/* ───── API Helper ───── */
async function deliveryApi(method, path, body = null) {
    const token = getDeliveryToken();
    const opts = {
        method,
        headers: {
            "Authorization": `Bearer ${token}`,
            "Content-Type": "application/json"
        }
    };
    if (body) opts.body = JSON.stringify(body);

    const res = await fetch(`${DELIVERY_API}${path}`, opts);

    if (res.status === 401) {
        localStorage.removeItem("delivery_token");
        localStorage.removeItem("delivery_user");
        window.location.href = "login.html";
        return null;
    }

    return res.json();
}

/* ───── Toast Notification ───── */
function showDeliveryToast(message, type = "success") {
    let toast = document.getElementById("deliveryToast");
    if (!toast) {
        toast = document.createElement("div");
        toast.id = "deliveryToast";
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 14px 20px;
            border-radius: 8px;
            color: white;
            font-size: 14px;
            font-weight: 500;
            opacity: 0;
            transition: opacity 0.3s;
            z-index: 99999;
            max-width: 300px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        `;
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.style.backgroundColor = type === "success" ? "#28a745" : type === "error" ? "#dc3545" : "#007bff";
    toast.style.opacity = "1";
    setTimeout(() => { toast.style.opacity = "0"; }, 3000);
}

/* ───── Bottom Nav Renderer ───── */
function renderDeliveryNav(activePage) {
    const pages = [
        { href: "dashboard.html", icon: "🏠", label: "Home" },
        { href: "assignments.html", icon: "📦", label: "Orders" },
        { href: "history.html", icon: "📋", label: "History" },
        { href: "earnings.html", icon: "💰", label: "Earnings" },
        { href: "salary.html", icon: "🧾", label: "Salary" },
        { href: "profile.html", icon: "👤", label: "Profile" }
    ];

    const nav = document.createElement("nav");
    nav.style.cssText = `
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: var(--color-surface);
        border-top: 1px solid var(--color-border);
        display: flex;
        justify-content: space-around;
        padding: 8px 0;
        z-index: 100;
    `;

    pages.forEach(page => {
        const isActive = page.href === activePage;
        const item = document.createElement("a");
        item.href = page.href;
        item.style.cssText = `
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
            text-decoration: none;
            color: ${isActive ? "var(--color-forest)" : "var(--color-ink-soft)"};
            font-size: 10px;
            padding: 4px 12px;
            border-radius: 8px;
            transition: color 0.2s;
        `;
        item.innerHTML = `<span style="font-size:20px">${page.icon}</span><span>${page.label}</span>`;
        nav.appendChild(item);
    });

    document.body.appendChild(nav);
    document.body.style.paddingBottom = "70px";
}

/* ───── Format Helpers ───── */
function formatDate(isoString) {
    if (!isoString) return "—";
    return new Date(isoString).toLocaleString("en-IN", {
        month: "short", day: "numeric",
        hour: "2-digit", minute: "2-digit"
    });
}

function formatCurrency(amount) {
    return `₹${(parseFloat(amount) || 0).toFixed(2)}`;
}

function formatStatus(status) {
    const map = {
        assigned: "Assigned",
        picked_up: "Picked Up",
        out_for_delivery: "Out For Delivery",
        delivered: "Delivered",
        failed: "Failed"
    };
    return map[status] || status;
}

function statusBadgeHTML(status) {
    const colors = {
        assigned: { bg: "#e7f3ff", color: "#0066cc" },
        picked_up: { bg: "#fff3cd", color: "#856404" },
        out_for_delivery: { bg: "#ffd9a0", color: "#7a4100" },
        delivered: { bg: "#d4edda", color: "#155724" },
        failed: { bg: "#f8d7da", color: "#721c24" }
    };
    const c = colors[status] || { bg: "#e9ecef", color: "#495057" };
    return `<span style="display:inline-block;padding:4px 10px;border-radius:20px;font-size:12px;font-weight:600;background:${c.bg};color:${c.color}">${formatStatus(status)}</span>`;
}
