// Tiny API client. Cookies carry the session, so we always send credentials.
const BASE = "/api";

async function req(path: string, opts: RequestInit = {}) {
  const res = await fetch(BASE + path, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    ...opts,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") {
        detail = body.detail;
      } else if (Array.isArray(body.detail)) {
        // FastAPI validation errors arrive as a list of {loc, msg, ...}.
        detail = body.detail.map((e: any) => e.msg).join("; ");
      } else if (body.detail) {
        detail = JSON.stringify(body.detail);
      }
    } catch {}
    throw new Error(detail);
  }
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res;
}

export const api = {
  get: (p: string) => req(p),
  post: (p: string, body?: any) =>
    req(p, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  put: (p: string, body?: any) =>
    req(p, { method: "PUT", body: JSON.stringify(body) }),
  del: (p: string) => req(p, { method: "DELETE" }),
  // Returns a download URL for CSV/PDF/ZIP endpoints.
  fileUrl: (p: string) => BASE + p,
};

export type Account = {
  id: string; name: string; type: string; description_plain?: string;
};
export type Company = { id: string; name: string; business_type: string; state: string };
