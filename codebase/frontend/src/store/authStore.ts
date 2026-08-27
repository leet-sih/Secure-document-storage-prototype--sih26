/**
 * authStore.ts — DEPRECATED. Replaced by AuthContext.tsx (CHANGES.md §5).
 *
 * Zustand and Axios have been removed from package.json. This file is kept as a
 * historical reference only. Do not import from it — import from AuthContext.tsx.
 *
 * Migration summary:
 *   - Zustand store  →  React Context + useReducer  (src/store/AuthContext.tsx)
 *   - Axios instance →  native fetch wrapper         (src/lib/apiClient.ts)
 *   - useAuthStore() →  useAuth()                    (from AuthContext.tsx)
 */
