// StudentSphere single-page UI. All data comes from the FastAPI backend.
import { api, ApiError } from "./api.js";
import { esc, fmtDate, timeAgo, avatar, icon, toast, openModal, closeModal, confirmDialog } from "./ui.js";

const view = document.getElementById("view");
const titleEl = document.getElementById("page-title");
const ROUTES = {
  dashboard: ["Dashboard", renderDashboard],
  students: ["Students", renderStudents],
  add: ["Add Student", (_, t) => renderForm(null, t)],
  edit: ["Edit Student", (arg, t) => renderForm(arg, t)],
  assistant: ["AI Assistant", renderAssistant],
  about: ["About", renderAbout],
};
const listState = { search: "", course: "", enrolled_from: "", enrolled_to: "", sort_by: "created_at", order: "desc", page: 1, page_size: 10 };
let renderToken = 0;

// ---------- helpers ----------
const loading = () => (view.innerHTML = `<div class="state"><div class="spinner" role="status" aria-label="Loading"></div></div>`);
function errorState(err, retry) {
  view.innerHTML = `<div class="card state">${icon("info", "ic ic-lg")}<h3>${err.status === 0 ? "Server unavailable" : "Something went wrong"}</h3>
    <p>${esc(err.message)}</p><button class="btn btn-primary" id="retry">Try again</button></div>`;
  document.getElementById("retry").onclick = retry;
}
const debounce = (fn, ms = 300) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };

// ---------- router ----------
function parseHash() {
  const parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean).map(decodeURIComponent);
  if (!parts.length) return ["dashboard"];
  if (parts[0] === "students" && parts[1] === "edit" && parts[2]) return ["edit", parts[2]];
  return ROUTES[parts[0]] ? [parts[0], parts[1]] : ["dashboard"];
}
async function route() {
  const [name, arg] = parseHash();
  const [title, fn] = ROUTES[name];
  titleEl.textContent = title;
  document.title = `${title} · StudentSphere`;
  document.querySelectorAll(".nav a[data-route]").forEach((a) => a.classList.toggle("active", a.dataset.route === (name === "edit" ? "students" : name)));
  closeSidebar();
  const token = ++renderToken;
  loading();
  try { await fn(arg, token); } catch (e) { if (token === renderToken) errorState(e instanceof ApiError ? e : new ApiError(-1, e.message), route); }
  view.focus({ preventScroll: true });
}
window.addEventListener("hashchange", route);

// ---------- dashboard ----------
async function renderDashboard(_, token) {
  const s = await api.stats();
  if (token !== renderToken) return;
  const max = Math.max(1, ...s.courses.map((c) => c.count));
  const card = (ic, n, label) => `<div class="card stat"><span class="badge">${icon(ic)}</span><div><b>${n}</b><span>${label}</span></div></div>`;
  view.innerHTML = `
    <div class="stats">
      ${card("users", s.total_students, "Total students")}
      ${card("cal", s.enrolled_this_month, "Enrolled this month")}
      ${card("book", s.course_count, "Courses / departments")}
      ${card("plus", s.recent_students.length, "Recently added")}
    </div>
    ${s.total_students === 0 ? `<div class="card state">${icon("users", "ic ic-lg")}<h3>No students yet</h3><p>Add your first student to see statistics here.</p><a class="btn btn-primary" href="#/add">Add student</a></div>` : `
    <div class="grid-2">
      <section class="card card-pad"><h2>Recently added</h2><p class="sub">The latest records saved to the database</p>
        <ul class="recent">${s.recent_students.map((st) => `
          <li data-id="${esc(st.student_id)}" tabindex="0">${avatar(st.full_name)}
            <div><div class="nm">${esc(st.full_name)}</div><div class="meta">${esc(st.student_id)} · ${esc(st.course || "No course")}</div></div>
            <span class="when">${timeAgo(st.created_at)}</span></li>`).join("")}</ul>
        <p style="margin-top:12px"><a href="#/students">View all students</a></p></section>
      <section class="card card-pad"><h2>Students by course</h2><p class="sub">Calculated from stored records</p>
        ${s.courses.length ? `<div class="bars">${s.courses.map((c) => `<div class="bar-row"><div class="lbl"><span>${esc(c.course)}</span><b>${c.count}</b></div><div class="bar"><i style="width:${(c.count / max) * 100}%"></i></div></div>`).join("")}</div>` : `<p class="sub">No courses assigned yet.</p>`}
      </section>
    </div>`}`;
  view.querySelectorAll(".recent li").forEach((li) => {
    const open = () => showProfile(li.dataset.id);
    li.onclick = open; li.onkeydown = (e) => { if (e.key === "Enter") open(); };
  });
}

// ---------- students table ----------
async function renderStudents(_, token) {
  const courses = await api.courses();
  if (token !== renderToken) return;
  view.innerHTML = `
    <div class="card">
      <div class="toolbar">
        <div class="search">${icon("search")}<input id="f-search" type="search" placeholder="Search name, ID, email or phone" maxlength="100" value="${esc(listState.search)}" aria-label="Search students"></div>
        <select id="f-course" aria-label="Filter by course"><option value="">All courses</option>${courses.map((c) => `<option ${c.course.toLowerCase() === listState.course.toLowerCase() && listState.course ? "selected" : ""} value="${esc(c.course)}">${esc(c.course)} (${c.count})</option>`).join("")}</select>
        <label style="display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-size:13px;color:var(--muted)">Enrolled
          <input id="f-from" type="date" style="width:auto;min-width:0" value="${esc(listState.enrolled_from)}" aria-label="Enrolled from">–
          <input id="f-to" type="date" style="width:auto;min-width:0" value="${esc(listState.enrolled_to)}" aria-label="Enrolled to"></label>
        <button class="btn" id="f-clear">Clear filters</button>
      </div>
      <div id="table-area"></div>
    </div>`;
  const reload = () => loadTable();
  const bind = (id, key, ev = "change") => document.getElementById(id).addEventListener(ev, (e) => { listState[key] = e.target.value; listState.page = 1; reload(); });
  document.getElementById("f-search").addEventListener("input", debounce((e) => { listState.search = e.target.value; listState.page = 1; reload(); }));
  bind("f-course", "course"); bind("f-from", "enrolled_from"); bind("f-to", "enrolled_to");
  document.getElementById("f-clear").onclick = () => {
    Object.assign(listState, { search: "", course: "", enrolled_from: "", enrolled_to: "", page: 1 });
    renderStudents(null, renderToken).catch((e) => errorState(e, route));
  };
  await loadTable();
}

const COLS = [["full_name", "Student"], ["email", "Email"], ["phone", "Phone"], ["course", "Course"], ["enrollment_date", "Enrolled"]];
let tableSeq = 0;
async function loadTable() {
  const area = document.getElementById("table-area");
  if (!area) return;
  const seq = ++tableSeq;
  let data;
  try { data = await api.listStudents(listState); }
  catch (e) { if (seq === tableSeq) area.innerHTML = `<div class="state"><h3>${e.status === 0 ? "Server unavailable" : "Could not load students"}</h3><p>${esc(e.message)}</p><button class="btn btn-primary" id="retry">Try again</button></div>`, document.getElementById("retry").onclick = loadTable; return; }
  if (seq !== tableSeq) return;
  if (data.page > data.total_pages) { listState.page = data.total_pages; return loadTable(); }

  const filtered = listState.search || listState.course || listState.enrolled_from || listState.enrolled_to;
  if (!data.total) {
    area.innerHTML = `<div class="state">${icon("users", "ic ic-lg")}<h3>${filtered ? "No students match your filters" : "No students yet"}</h3>
      <p>${filtered ? "Try a different search or clear the filters." : "Add your first student to get started."}</p>
      ${filtered ? "" : `<a class="btn btn-primary" href="#/add">Add student</a>`}</div>`;
    return;
  }
  const arrow = (k) => (listState.sort_by === k ? icon(listState.order === "asc" ? "up" : "down") : "");
  const from = (data.page - 1) * data.page_size + 1, to = from + data.items.length - 1;
  area.innerHTML = `
    <div class="table-wrap"><table>
      <thead><tr><th><button data-sort="student_id">ID ${arrow("student_id")}</button></th>
        ${COLS.map(([k, l]) => `<th><button data-sort="${k}">${l} ${arrow(k)}</button></th>`).join("")}<th style="text-align:right">Actions</th></tr></thead>
      <tbody>${data.items.map((s) => `<tr>
        <td class="mono">${esc(s.student_id)}</td>
        <td><div class="who">${avatar(s.full_name)}<div><b>${esc(s.full_name)}</b></div></div></td>
        <td>${esc(s.email)}</td><td>${esc(s.phone || "—")}</td>
        <td>${s.course ? `<span class="chip">${esc(s.course)}</span>` : "—"}</td><td>${fmtDate(s.enrollment_date)}</td>
        <td><div class="actions">
          <button class="icon-btn" data-view="${esc(s.student_id)}" aria-label="View ${esc(s.full_name)}" title="View">${icon("eye")}</button>
          <a class="icon-btn" href="#/students/edit/${encodeURIComponent(s.student_id)}" aria-label="Edit ${esc(s.full_name)}" title="Edit">${icon("edit")}</a>
          <button class="icon-btn danger" data-del="${esc(s.student_id)}" data-name="${esc(s.full_name)}" aria-label="Delete ${esc(s.full_name)}" title="Delete">${icon("trash")}</button></div></td></tr>`).join("")}</tbody>
    </table></div>
    <div class="pager"><span>Showing ${from}–${to} of ${data.total} student${data.total === 1 ? "" : "s"}</span>
      <div class="pg"><label>Rows <select id="f-size">${[5, 10, 25, 50].map((n) => `<option ${n === listState.page_size ? "selected" : ""}>${n}</option>`).join("")}</select></label>
        <button class="btn btn-sm" id="prev" ${data.page <= 1 ? "disabled" : ""}>Previous</button>
        <span>Page ${data.page} of ${data.total_pages}</span>
        <button class="btn btn-sm" id="next" ${data.page >= data.total_pages ? "disabled" : ""}>Next</button></div></div>`;

  area.querySelectorAll("[data-sort]").forEach((b) => b.onclick = () => {
    const k = b.dataset.sort;
    listState.order = listState.sort_by === k && listState.order === "asc" ? "desc" : "asc";
    listState.sort_by = k; listState.page = 1; loadTable();
  });
  area.querySelectorAll("[data-view]").forEach((b) => b.onclick = () => showProfile(b.dataset.view));
  area.querySelectorAll("[data-del]").forEach((b) => b.onclick = () => deleteFlow(b.dataset.del, b.dataset.name, loadTable));
  document.getElementById("f-size").onchange = (e) => { listState.page_size = +e.target.value; listState.page = 1; loadTable(); };
  document.getElementById("prev").onclick = () => { listState.page--; loadTable(); };
  document.getElementById("next").onclick = () => { listState.page++; loadTable(); };
}

// ---------- profile + delete ----------
async function showProfile(id) {
  let s;
  try { s = await api.getStudent(id); } catch (e) { return toast(e.message, "error"); }
  const row = (k, v) => `<dt>${k}</dt><dd>${v ? esc(v) : "—"}</dd>`;
  const modal = openModal(`
    <div class="modal-head"><h2>Student profile</h2><button class="icon-btn" data-close aria-label="Close">${icon("x")}</button></div>
    <div class="modal-body">
      <div class="profile-head">${avatar(s.full_name, true)}<div><h3>${esc(s.full_name)}</h3><span class="chip">${esc(s.student_id)}</span></div></div>
      <dl class="details">${row("Email", s.email)}${row("Phone", s.phone)}${row("Date of birth", s.date_of_birth && fmtDate(s.date_of_birth))}
        ${row("Course", s.course)}${row("Enrolled", s.enrollment_date && fmtDate(s.enrollment_date))}${row("Address", s.address)}
        ${row("Created", new Date(s.created_at + "Z").toLocaleString())}${row("Last updated", new Date(s.updated_at + "Z").toLocaleString())}</dl>
    </div>
    <div class="modal-foot"><button class="btn btn-danger" id="p-del">${icon("trash")}Delete</button>
      <a class="btn btn-primary" href="#/students/edit/${encodeURIComponent(s.student_id)}" data-close>${icon("edit")}Edit</a></div>`);
  modal.querySelector("#p-del").onclick = () => { closeModal(); deleteFlow(s.student_id, s.full_name, () => (parseHash()[0] === "students" ? loadTable() : route())); };
}

async function deleteFlow(id, name, after) {
  const ok = await confirmDialog({ title: "Delete student?", message: `This permanently deletes <strong>${esc(name)}</strong> (${esc(id)}). This cannot be undone.` });
  if (!ok) return;
  try { await api.deleteStudent(id); toast(`Deleted ${name}.`); after?.(); }
  catch (e) { toast(e.message, "error"); }
}

// ---------- add / edit form ----------
const FIELDS = ["student_id", "full_name", "date_of_birth", "email", "phone", "course", "enrollment_date", "address"];
const today = () => new Date().toISOString().slice(0, 10);
const RULES = {
  student_id: (v) => (!v ? "Student ID is required." : /^[A-Za-z0-9][A-Za-z0-9\-_]{1,19}$/.test(v) ? "" : "Use 2–20 letters, digits, '-' or '_'."),
  full_name: (v) => (!v ? "Full name is required." : v.length < 2 ? "Name must be at least 2 characters." : ""),
  date_of_birth: (v) => (!v ? "Date of birth is required." : v >= today() ? "Date of birth must be in the past." : v < "1900-01-01" ? "Date must be after 1900." : ""),
  email: (v) => (!v ? "Email is required." : /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v) ? "" : "Enter a valid email address."),
  phone: (v) => (!v || /^\+?[0-9][0-9\s\-()]{5,17}[0-9]$/.test(v) ? "" : "Enter a valid phone number (7–20 digits)."),
};

async function renderForm(editId, token) {
  const existing = editId ? await api.getStudent(editId) : null;
  if (token !== renderToken) return;
  const courses = await api.courses().catch(() => []);
  const v = (k) => esc(existing?.[k] ?? "");
  const field = (name, label, input, { req = false, hint = "", full = false } = {}) => `
    <div class="field ${full ? "full" : ""}" data-field="${name}"><label for="${name}">${label}${req ? ' <span class="req" aria-hidden="true">*</span>' : ""}</label>${input}
      ${hint ? `<div class="hint">${hint}</div>` : ""}<div class="err" id="${name}-err" role="alert"></div></div>`;
  view.innerHTML = `<div class="card card-pad form-card">
    <h2>${existing ? "Edit student" : "New student"}</h2><p class="sub">Fields marked <span class="req">*</span> are required.</p>
    <div id="form-banner"></div>
    <form id="student-form" class="form" novalidate>
      ${field("student_id", "Student ID", `<input id="student_id" name="student_id" maxlength="20" value="${v("student_id")}" placeholder="STU-1001" autocomplete="off">`, { req: true, hint: "Unique. Letters, digits, '-' or '_'." })}
      ${field("full_name", "Full name", `<input id="full_name" name="full_name" maxlength="100" value="${v("full_name")}" placeholder="Aarav Sharma">`, { req: true })}
      ${field("date_of_birth", "Date of birth", `<input id="date_of_birth" name="date_of_birth" type="date" max="${today()}" value="${v("date_of_birth")}">`, { req: true })}
      ${field("email", "Email address", `<input id="email" name="email" type="email" maxlength="254" value="${v("email")}" placeholder="name@example.com">`, { req: true })}
      ${field("phone", "Phone number", `<input id="phone" name="phone" type="tel" maxlength="20" value="${v("phone")}" placeholder="+91 98765 43210">`)}
      ${field("course", "Course / department", `<input id="course" name="course" maxlength="100" list="course-list" value="${v("course")}" placeholder="Computer Science"><datalist id="course-list">${courses.map((c) => `<option value="${esc(c.course)}">`).join("")}</datalist>`)}
      ${field("enrollment_date", "Enrollment date", `<input id="enrollment_date" name="enrollment_date" type="date" value="${v("enrollment_date")}">`)}
      ${field("address", "Address", `<textarea id="address" name="address" maxlength="500">${v("address")}</textarea>`, { full: true })}
      <div class="form-actions"><a class="btn" href="#/students">Cancel</a><button class="btn btn-primary" type="submit" id="save-btn">${existing ? "Save changes" : "Save student"}</button></div>
    </form></div>`;

  const form = document.getElementById("student-form");
  const setErr = (name, msg) => {
    const f = form.querySelector(`[data-field="${name}"]`);
    f.classList.toggle("invalid", !!msg);
    f.querySelector(".err").textContent = msg;
  };
  FIELDS.forEach((n) => RULES[n] && form.elements[n].addEventListener("blur", () => setErr(n, RULES[n](form.elements[n].value.trim()))));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    document.getElementById("form-banner").innerHTML = "";
    const body = {};
    FIELDS.forEach((n) => (body[n] = form.elements[n].value.trim() || null));
    let bad = null;
    for (const n of Object.keys(RULES)) { const m = RULES[n](body[n] || ""); setErr(n, m); if (m && !bad) bad = n; }
    if (bad) return form.elements[bad].focus();
    const btn = document.getElementById("save-btn");
    btn.disabled = true; btn.textContent = "Saving…";
    try {
      const saved = existing ? await api.updateStudent(existing.student_id, body) : await api.createStudent(body);
      toast(existing ? `Updated ${saved.full_name}.` : `Added ${saved.full_name}.`);
      location.hash = "#/students";
    } catch (err) {
      btn.disabled = false; btn.textContent = existing ? "Save changes" : "Save student";
      const fieldErrs = (err.errors || []).filter((x) => FIELDS.includes(x.field));
      fieldErrs.forEach((x) => setErr(x.field, x.message));
      if (fieldErrs.length) form.elements[fieldErrs[0].field].focus();
      if (!fieldErrs.length || err.status === 0) document.getElementById("form-banner").innerHTML = `<div class="banner">${esc(err.message)}</div>`;
      else if (err.status === 409) document.getElementById("form-banner").innerHTML = `<div class="banner">${esc(err.message)}</div>`;
    }
  });
}

// ---------- AI assistant ----------
async function renderAssistant() {
  if (document.body.dataset.aiEnabled !== "true") { view.innerHTML = `<div class="card state"><h3>AI assistant is disabled</h3><p>Set ENABLE_AI=true in .env to enable it.</p></div>`; return; }
  const st = await api.aiStatus();
  view.innerHTML = `<div class="card card-pad" style="max-width:860px">
    <h2>Ask about your students</h2>
    <p class="sub">Read-only. Answers come from your database via approved queries; the local model (${esc(st.model)}) only words the result. It cannot change data.</p>
    <div class="suggest">${st.examples.map((q) => `<button type="button">${esc(q)}</button>`).join("")}</div>
    <div class="chat" id="chat" aria-live="polite"><div class="msg bot">Hi! Pick a question above or type your own.</div></div>
    <form class="ask" id="ask-form"><input id="ask-input" maxlength="300" placeholder="e.g. How many students are registered?" aria-label="Your question" autocomplete="off"><button class="btn btn-primary" id="ask-btn">Ask</button></form></div>`;
  const chat = document.getElementById("chat"), input = document.getElementById("ask-input"), btn = document.getElementById("ask-btn");
  const add = (cls, text, note = "") => { const d = document.createElement("div"); d.className = `msg ${cls}`; d.textContent = text; if (note) { const s = document.createElement("small"); s.textContent = note; d.appendChild(s); } chat.appendChild(d); chat.scrollTop = chat.scrollHeight; return d; };
  async function ask(q) {
    if (q.trim().length < 3) return;
    add("user", q); input.value = ""; btn.disabled = true;
    const pending = add("bot", "Thinking…");
    try {
      const r = await api.ask(q);
      pending.remove();
      add("bot", r.answer, r.ai_available ? `Source: database · operation: ${r.operation}` : "Local AI model not reachable. Showing the direct database result.");
    } catch (e) { pending.remove(); add("bot", e.message); }
    btn.disabled = false; input.focus();
  }
  view.querySelectorAll(".suggest button").forEach((b) => (b.onclick = () => ask(b.textContent)));
  document.getElementById("ask-form").onsubmit = (e) => { e.preventDefault(); ask(input.value); };
}

// ---------- about ----------
function renderAbout() {
  view.innerHTML = `<div class="card card-pad" style="max-width:760px"><h2>About StudentSphere</h2>
    <p class="sub">Student Database Management System built with Python, FastAPI and SQLite.</p>
    <ul class="about-list"><li>Developer: Narendra Vishnoi</li><li>Organization: EWB Edu Tech Pvt. Ltd. (Python Backend Development internship)</li>
    <li>Backend: FastAPI, SQLAlchemy, Pydantic, SQLite</li><li>Interactive API docs: <a href="/docs" target="_blank" rel="noopener">/docs</a> and <a href="/redoc" target="_blank" rel="noopener">/redoc</a></li>
    <li>Health check: <a href="/health" target="_blank" rel="noopener">/health</a></li></ul></div>`;
}

// ---------- shell: sidebar, health ----------
const sidebar = document.getElementById("sidebar"), scrim = document.getElementById("scrim");
function closeSidebar() { sidebar.classList.remove("open"); scrim.classList.remove("open"); }
document.getElementById("menu-btn").onclick = () => { sidebar.classList.add("open"); scrim.classList.add("open"); };
scrim.onclick = closeSidebar;

async function pingServer() {
  const el = document.getElementById("server-status");
  try { await api.health(); el.className = "status ok"; el.lastElementChild.textContent = "Server connected"; }
  catch { el.className = "status down"; el.lastElementChild.textContent = "Server unreachable"; }
}
pingServer(); setInterval(pingServer, 30000);
route();
