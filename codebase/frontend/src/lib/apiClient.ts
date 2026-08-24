/**
 * apiClient.ts — the single Axios instance every API call goes through.
 *
 * RESPONSIBILITIES (prototype):
 *   - baseURL "/api/v1" (Vite proxies this to the Flask backend in dev).
 *   - Request interceptor: attach `Authorization: Bearer <accessToken>` from the auth store.
 *   - Response interceptor: on 401, clear the session and redirect to /login.
 *   - Never log request/response bodies (may contain PII).
 *
 * PROTOTYPE SIMPLIFICATION:
 *   No silent token-refresh/retry logic — there's no refresh token yet (access token is
 *   long-lived, see authStore). Production adds a refresh interceptor here — auth_plan.md.
 *
 * EXPORTS: `api` (configured AxiosInstance).
 */
import axios from "axios";
import { useAuthStore } from "../store/authStore";

export const api = axios.create({
  baseURL: "/api/v1",
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore.getState().clear();
      if (window.location.pathname !== "/login") window.location.assign("/login");
    }
    return Promise.reject(err);
  }
);
