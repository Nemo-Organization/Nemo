import axios, { AxiosError } from "axios";

export type PaginationParams = {
  limit?: number;
  offset?: number;
};

export type PaginatedResponse<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

export type ApiErrorBody = {
  error: {
    code: string;
    message: string;
    request_id: string;
    current_transfer?: unknown;
    assessment?: unknown;
  };
};

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/v1";

let csrfToken: string | null = null;

export function setCsrfToken(token: string | null) {
  csrfToken = token;
}

export function getCsrfToken() {
  return csrfToken;
}

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  timeout: 25_000,
  headers: {
    Accept: "application/json",
  },
});

const MUTATING_METHODS = new Set(["post", "put", "patch", "delete"]);

apiClient.interceptors.request.use((config) => {
  const method = config.method?.toLowerCase();
  if (method && MUTATING_METHODS.has(method) && csrfToken) {
    config.headers.set("X-CSRF-Token", csrfToken);
  }
  return config;
});

export function extractApiError(error: unknown): ApiErrorBody["error"] | null {
  if (error instanceof AxiosError) {
    const data = error.response?.data as Partial<ApiErrorBody> | undefined;
    if (data?.error?.code) return data.error;
  }
  return null;
}

export function buildApiUrl(path: string) {
  const base = API_BASE_URL.replace(/\/$/, "");
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${base}${normalized}`;
}
