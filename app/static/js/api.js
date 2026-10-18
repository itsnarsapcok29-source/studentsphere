// Thin wrapper around fetch() for the StudentSphere FastAPI backend.
export class ApiError extends Error {
  constructor(status, message, errors = []) {
    super(message);
    this.status = status;
    this.errors = errors;
  }
}

async function request(method, url, body) {
  let res;
  try {
    res = await fetch(url, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, "Cannot reach the server. Check that StudentSphere is running and try again.");
  }
  if (res.status === 204) return null;
  let data = null;
  try { data = await res.json(); } catch { /* non-JSON body */ }
  if (!res.ok) throw new ApiError(res.status, data?.detail || `Request failed (${res.status}).`, data?.errors || []);
  return data;
}

const qs = (params) => {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== "" && v != null) p.set(k, v); });
  const s = p.toString();
  return s ? `?${s}` : "";
};

export const api = {
  listStudents: (params) => request("GET", `/students${qs(params)}`),
  getStudent: (id) => request("GET", `/students/${encodeURIComponent(id)}`),
  createStudent: (body) => request("POST", "/students", body),
  updateStudent: (id, body) => request("PUT", `/students/${encodeURIComponent(id)}`, body),
  deleteStudent: (id) => request("DELETE", `/students/${encodeURIComponent(id)}`),
  stats: () => request("GET", "/api/stats"),
  courses: () => request("GET", "/api/courses"),
  ask: (question) => request("POST", "/api/ai/ask", { question }),
  aiStatus: () => request("GET", "/api/ai/status"),
  health: () => request("GET", "/health"),
};
