const configuredApi = String(import.meta.env.VITE_API_URL || '').trim();
const API_URL = (configuredApi && !configuredApi.includes('sih100-production.up.railway.app')
  ? configuredApi
  : 'https://api.chatlyme.xyz').replace(/\/+$/, '').replace(/\/api$/, '');

export async function apiRequest<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const isFormData = options.body instanceof FormData;

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(options.headers || {}),
    },
  });

  const contentType = response.headers.get("content-type") || "";

  const data = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const detail =
      typeof data === "object" &&
      data !== null &&
      "detail" in data
        ? String((data as { detail: unknown }).detail)
        : `Request failed with HTTP ${response.status}`;

    throw new Error(detail);
  }

  return data as T;
}

export { API_URL };
