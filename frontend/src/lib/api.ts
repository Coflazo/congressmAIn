export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

type ApiErrorShape = {
  error?: {
    message?: string;
  };
};

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as ApiErrorShape;
    throw new Error(payload.error?.message ?? `Request failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}
