const TENANT  = process.env.NEXT_PUBLIC_TENANT_API_URL  ?? "/api/concierge/tenant";
const HANDOFF = process.env.NEXT_PUBLIC_HANDOFF_URL     ?? "/api/concierge/handoff";
const SKILLS  = process.env.NEXT_PUBLIC_SKILLS_URL      ?? "/api/concierge/skills";

export interface Escalation {
  id: string;
  status: string;
  offered_to: string | null;
  accepted_by: string | null;
  agent_phone: string | null;
}

export async function api<T>(
  path: string,
  init?: RequestInit & { auth?: string; tenantId?: string },
): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  if (init?.auth)     headers.set("Authorization", `Bearer ${init.auth}`);
  if (init?.tenantId) headers.set("X-Tenant-Id", init.tenantId);

  const res = await fetch(path, { ...init, headers });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json() as Promise<T>;
}

export const endpoints = {
  escalation:   (id: string) => `${HANDOFF}/escalations/${id}`,
  acceptOffer:  (id: string) => `${HANDOFF}/escalations/${id}/accept`,
  agentSocket:  (id: string) => {
    const base = HANDOFF.replace(/^http/, "ws");
    return `${base}/agents/${id}/ws`;
  },
  features:     (tid: string) => `${TENANT}/tenants/${tid}/features`,
  ratings:      () => `${SKILLS}/ratings`,
  earnings:     () => `${SKILLS}/earnings`,
};
