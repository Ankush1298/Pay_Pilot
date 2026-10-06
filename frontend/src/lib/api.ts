export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

type RequestOptions = Omit<RequestInit, "body"> & { body?: any };

async function request(endpoint: string, options: RequestOptions = {}) {
  const url = `/api${endpoint}`;
  const headers = new Headers(options.headers || {});
  let body = options.body;
  if (body && typeof body === "object" && !(body instanceof FormData) && !(body instanceof Blob) && !(body instanceof ArrayBuffer)) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(body);
  }
  const res = await fetch(url, { ...options, headers, body, credentials: "same-origin" });
  const data = await res.json().catch(() => null);   // non-JSON (e.g. a proxy error page) falls through to the status text

  if (res.status === 401 && typeof window !== "undefined" && !endpoint.startsWith("/auth/login") && !endpoint.startsWith("/auth/register")) {
    window.dispatchEvent(new Event("paypilot:unauthorized"));
  }
  if (!res.ok) {
    throw new ApiError(
      res.status,
      data?.detail?.code || "unknown_error",
      data?.detail?.message || res.statusText
    );
  }
  return data;
}

export const api = {
  auth: {
    registerOpts: (username: string) => request("/auth/register/options", { method: "POST", body: { username } }),
    registerVerify: (body: any) => request("/auth/register/verify", { method: "POST", body }),
    loginOpts: () => request("/auth/login/options", { method: "POST" }),
    loginVerify: (credential: any) => request("/auth/login/verify", { method: "POST", body: { credential } }),
    logout: () => request("/auth/logout", { method: "POST" }),
    me: () => request("/auth/me"),
    session: () => request("/auth/session"),
  },
  state: {
    get: () => request("/state"),
  },
  agent: {
    chat: (message: string, conversation_id?: string) => request("/agent/chat", { method: "POST", body: { message, conversation_id } }),
    prepare: (option_id: string, conversation_id?: string) => request("/agent/prepare", { method: "POST", body: { option_id, conversation_id } }),
    manage: (bookingId: string, action: "cancel" | "modify", units?: number) => request(`/agent/bookings/${bookingId}/${action}`, { method: "POST", body: { units } }),
  },
  chats: {
    list: () => request("/chat/conversations"),
    create: () => request("/chat/conversations", { method: "POST" }),
    get: (id: string) => request(`/chat/conversations/${id}`),
    editContext: (id: string, context: Record<string, unknown>) => request(`/chat/conversations/${id}/context`, { method: "PATCH", body: { context } }),
    remove: (id: string) => request(`/chat/conversations/${id}`, { method: "DELETE" }),
  },
  intents: {
    approvalOpts: (id: string) => request(`/intents/${id}/approval-options`, { method: "POST" }),
    approve: (id: string, credential: any) => request(`/intents/${id}/approve`, { method: "POST", body: { credential } }),
    reject: (id: string) => request(`/intents/${id}/reject`, { method: "POST" }),
  },
  devices: {
    approve: (id: string) => request(`/devices/${id}/approve`, { method: "POST" }),
    block: (id: string) => request(`/devices/${id}/block`, { method: "POST" }),
  },
  policy: {
    initial: (policy: any) => request("/onboarding/policy", { method: "POST", body: { policy } }),
    complete: () => request("/onboarding/complete", { method: "POST" }),
    propose: (policy: any) => request("/policy/propose", { method: "POST", body: { policy } }),
  },
  connections: {
    start: (domain: string) => request(`/connections/${encodeURIComponent(domain)}/start`, { method: "POST" }),
    disconnect: (domain: string) => request(`/connections/${encodeURIComponent(domain)}`, { method: "DELETE" }),
  },
  passkeys: {
    registerOpts: () => request("/passkeys/register/options", { method: "POST" }),
    registerVerify: (body: any) => request("/passkeys/register/verify", { method: "POST", body }),
  },
  lab: {
    run: (scenario: string) => request("/lab/run", { method: "POST", body: { scenario } }),
  }
};
