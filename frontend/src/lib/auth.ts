import { API_URL } from "./utils";

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  org_id: string;
  role: string;
  email_verified: boolean;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
}

const TOKEN_KEY = "bonito_access_token";
const REFRESH_KEY = "bonito_refresh_token";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(tokens: AuthTokens) {
  localStorage.setItem(TOKEN_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
}

export function clearTokens() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

// ── Token refresh mutex ──
// Prevents multiple concurrent 401 responses from triggering parallel refreshes.
let _refreshPromise: Promise<boolean> | null = null;

async function _doTokenRefresh(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  try {
    const res = await fetch(`${API_URL}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!res.ok) return false;

    const tokens: AuthTokens = await res.json();
    setTokens(tokens);
    return true;
  } catch {
    return false;
  }
}

/**
 * Attempt to refresh the access token. Uses a mutex so only one refresh
 * runs at a time — concurrent callers share the same promise.
 */
async function refreshAccessToken(): Promise<boolean> {
  if (_refreshPromise) return _refreshPromise;

  _refreshPromise = _doTokenRefresh().finally(() => {
    _refreshPromise = null;
  });

  return _refreshPromise;
}

export async function apiRequest(path: string, options: RequestInit = {}) {
  const token = getAccessToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> || {}),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

  // On 401, attempt a silent token refresh and retry once
  if (res.status === 401 && token) {
    const refreshed = await refreshAccessToken();

    if (refreshed) {
      // Retry the original request with the new token
      const newToken = getAccessToken();
      const retryHeaders: Record<string, string> = {
        ...headers,
        Authorization: `Bearer ${newToken}`,
      };
      return fetch(`${API_URL}${path}`, { ...options, headers: retryHeaders });
    }

    // Refresh failed — session is dead, redirect to login
    clearTokens();
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
  }

  return res;
}

export async function register(email: string, password: string, name: string) {
  let res: Response;
  const maxRetries = 2;
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      res = await fetch(`${API_URL}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, name }),
      });
      break;
    } catch {
      if (attempt < maxRetries) {
        await new Promise((r) => setTimeout(r, 1000 * (attempt + 1)));
        continue;
      }
      throw new Error("Unable to reach the server. Please check your connection and try again.");
    }
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    const msg = data.error?.message || data.detail || "";
    if (res.status === 409) throw new Error("An account with this email already exists.");
    if (res.status === 422) throw new Error(msg || "Please check your password meets the requirements.");
    if (res.status === 429) throw new Error("Too many attempts. Please wait a minute and try again.");
    if (res.status >= 500) throw new Error("Something went wrong on our end. Please try again in a moment.");
    throw new Error(msg || "Registration failed. Please try again.");
  }
  return res.json();
}

export async function login(email: string, password: string): Promise<AuthTokens> {
  let res: Response;
  const maxRetries = 2;
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      res = await fetch(`${API_URL}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      break; // success — got a response
    } catch {
      if (attempt < maxRetries) {
        await new Promise((r) => setTimeout(r, 1000 * (attempt + 1))); // 1s, 2s backoff
        continue;
      }
      throw new Error("Unable to reach the server. Please check your connection and try again.");
    }
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    const msg = data.error?.message || data.detail || "";
    // Translate cryptic backend codes to human-friendly messages
    if (res.status === 401) throw new Error("Invalid email or password.");
    if (res.status === 403) throw new Error(msg || "Please verify your email before logging in.");
    if (res.status === 429) throw new Error("Too many login attempts. Please wait a minute and try again.");
    if (res.status >= 500) throw new Error("Something went wrong on our end. Please try again in a moment.");
    throw new Error(msg || "Login failed. Please try again.");
  }
  const tokens = await res.json();
  setTokens(tokens);
  return tokens;
}

export async function verifyEmail(token: string) {
  const res = await fetch(`${API_URL}/api/auth/verify-email`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.error?.message || data.detail || "Verification failed");
  }
  return res.json();
}

export async function resendVerification(email: string) {
  const res = await fetch(`${API_URL}/api/auth/resend-verification`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.error?.message || data.detail || "Failed to resend");
  }
  return res.json();
}

export async function forgotPassword(email: string) {
  const res = await fetch(`${API_URL}/api/auth/forgot-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  return res.json();
}

export async function resetPassword(token: string, password: string) {
  const res = await fetch(`${API_URL}/api/auth/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, password }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.error?.message || data.detail || "Reset failed");
  }
  return res.json();
}

export async function getMe(): Promise<AuthUser | null> {
  const token = getAccessToken();
  if (!token) return null;
  try {
    const res = await fetch(`${API_URL}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function logout() {
  const token = getAccessToken();
  if (token) {
    try {
      await fetch(`${API_URL}/api/auth/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {}
  }
  clearTokens();
}
