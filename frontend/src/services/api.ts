/**
 * Axios API Client.
 *
 * Configured with base URL, JWT interceptor, and centralized error handling.
 */

import axios, { AxiosError } from "axios";
import type { ApiError } from "@/types";

const API_BASE_URL = import.meta.env.VITE_API_URL || "/api/v1";

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
    "X-Requested-With": "XMLHttpRequest",
  },
  withCredentials: true,
});

// Request interceptor: attach JWT token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: handle 401 globally
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiError>) => {
    if (error.response?.status === 401) {
      // Avoid redirect loop on the login page itself
      if (!window.location.pathname.includes("/login")) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("user");
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

let warmedUp = false;

/**
 * Open connections to the API and wake the server (if it is asleep) while the
 * user is still on the login page, so the login request does not pay for it.
 * Fire-and-forget: errors are ignored and nothing is read from the response.
 */
export function warmUpApi(): void {
  if (warmedUp) return;
  warmedUp = true;
  try {
    const base = new URL(API_BASE_URL, window.location.href);
    if (base.origin !== window.location.origin) {
      // Credentialed connection for the API calls themselves (withCredentials).
      const link = document.createElement("link");
      link.rel = "preconnect";
      link.href = base.origin;
      document.head.appendChild(link);
    }
    // Plain GET, no custom headers, so no CORS preflight. Its connection is the
    // uncredentialed one that CORS preflights use.
    fetch(`${base.href.replace(/\/$/, "")}/auth/health`, { mode: "no-cors", cache: "no-store" }).catch(
      () => undefined
    );
  } catch {
    // Warm-up is best effort only.
  }
}

/**
 * Extract a human-readable error message from an Axios error.
 */
export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const apiError = error.response?.data as ApiError | undefined;
    return apiError?.message || error.message || "An unexpected error occurred";
  }
  return "An unexpected error occurred";
}

export default api;
