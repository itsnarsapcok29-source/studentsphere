// Small UI helpers: escaping, formatting, toasts, modals.
const ESC = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
export const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ESC[c]);

export function parseDate(iso) {
  if (!iso) return null;
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d);
}
export function fmtDate(iso) {
  const d = parseDate(iso);
  return d ? d.toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" }) : "—";
}
export function timeAgo(isoUtc) {
  const t = new Date(isoUtc.endsWith("Z") ? isoUtc : isoUtc + "Z");
  const s = Math.max(0, (Date.now() - t.getTime()) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return `${Math.floor(s / 86400)} d ago`;
}

const COLORS = ["#4f46e5", "#0891b2", "#0f9d63", "#c2410c", "#9333ea", "#be185d", "#0369a1", "#65a30d"];
export function avatar(name, large = false) {
  const parts = String(name).trim().split(/\s+/);
  const initials = ((parts[0]?.[0] || "") + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
  let h = 0;
  for (const ch of name) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return `<span class="avatar${large ? " lg" : ""}" style="background:${COLORS[h % COLORS.length]}" aria-hidden="true">${esc(initials)}</span>`;
}

export const icon = (id, cls = "ic") => `<svg class="${cls}"><use href="#i-${id}"/></svg>`;

export function toast(message, type = "success") {
  const el = document.createElement("div");
  el.className = `toast ${type === "error" ? "error" : ""}`;
  el.textContent = message;
  document.getElementById("toasts").appendChild(el);
  setTimeout(() => el.remove(), type === "error" ? 6000 : 3500);
}

// ---- Modal -------------------------------------------------------------
const root = () => document.getElementById("modal-root");
let lastFocus = null;
export function openModal(html, { onClose } = {}) {
  lastFocus = document.activeElement;
  const r = root();
  r.innerHTML = `<div class="modal" role="dialog" aria-modal="true">${html}</div>`;
  r.classList.add("open");
  r._onClose = onClose;
  r.querySelector("[data-close]")?.focus();
  return r.querySelector(".modal");
}
export function closeModal() {
  const r = root();
  r.classList.remove("open");
  r.innerHTML = "";
  r._onClose?.();
  lastFocus?.focus?.();
}
document.addEventListener("keydown", (e) => { if (e.key === "Escape" && root().classList.contains("open")) closeModal(); });
document.addEventListener("click", (e) => {
  if (e.target === root() || e.target.closest("[data-close]")) closeModal();
});

export function confirmDialog({ title, message, confirmLabel = "Delete", danger = true }) {
  return new Promise((resolve) => {
    const modal = openModal(`
      <div class="modal-head"><h2>${esc(title)}</h2><button class="icon-btn" data-close aria-label="Close">${icon("x")}</button></div>
      <div class="modal-body"><p>${message}</p></div>
      <div class="modal-foot"><button class="btn" data-close>Cancel</button>
      <button class="btn ${danger ? "btn-danger" : "btn-primary"}" id="confirm-ok">${esc(confirmLabel)}</button></div>`,
      { onClose: () => resolve(false) });
    modal.querySelector("#confirm-ok").addEventListener("click", () => {
      root()._onClose = null; closeModal(); resolve(true);
    });
  });
}
