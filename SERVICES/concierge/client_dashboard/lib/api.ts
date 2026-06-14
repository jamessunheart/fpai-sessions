const TENANT = process.env.NEXT_PUBLIC_TENANT_API_URL ?? "/api/concierge/tenant";

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
  start:       () =>                    `${TENANT}/onboarding/start`,
  knowledge:   (tid: string) =>         `${TENANT}/onboarding/${tid}/knowledge`,
  phoneTrial:  (tid: string) =>         `${TENANT}/onboarding/${tid}/phone-trial`,
  persona:     (tid: string) =>         `${TENANT}/onboarding/${tid}/persona`,
  checkout:    (tid: string) =>         `${TENANT}/onboarding/${tid}/checkout`,
  status:      (tid: string) =>         `${TENANT}/onboarding/${tid}/status`,
  features:    (tid: string) =>         `${TENANT}/tenants/${tid}/features`,
};
