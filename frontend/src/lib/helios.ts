/**
 * Helios — Lightweight frontend observability client.
 *
 * Captures errors and events, batches them, and sends to the backend
 * proxy endpoint which forwards to GCS for Helios ingestion.
 *
 * All events are tagged with the user's org_id for multi-tenant isolation.
 */

import { apiRequest } from "./auth";

interface HeliosEvent {
  level: "info" | "warning" | "error" | "critical";
  message: string;
  logger?: string;
  request_id?: string;
  exception?: {
    type: string;
    value: string;
    stacktrace?: string;
  };
  extra?: Record<string, unknown>;
}

// Buffer events and flush periodically to avoid per-event network overhead
const _buffer: HeliosEvent[] = [];
const FLUSH_INTERVAL_MS = 5000;
const MAX_BUFFER_SIZE = 50;
let _flushTimer: ReturnType<typeof setInterval> | null = null;

function _startFlushTimer() {
  if (_flushTimer) return;
  _flushTimer = setInterval(_flush, FLUSH_INTERVAL_MS);
}

async function _flush() {
  if (_buffer.length === 0) return;

  const batch = _buffer.splice(0, MAX_BUFFER_SIZE);
  try {
    await apiRequest("/api/frontend-events", {
      method: "POST",
      body: JSON.stringify({ events: batch }),
    });
  } catch {
    // Re-add events on failure (best-effort, cap at MAX_BUFFER_SIZE)
    if (_buffer.length < MAX_BUFFER_SIZE) {
      _buffer.unshift(...batch.slice(0, MAX_BUFFER_SIZE - _buffer.length));
    }
  }
}

function _emit(event: HeliosEvent) {
  _buffer.push(event);
  _startFlushTimer();

  // Flush immediately if buffer is full
  if (_buffer.length >= MAX_BUFFER_SIZE) {
    _flush();
  }
}

/**
 * Report an error to Helios. Call from ErrorBoundary, catch blocks, etc.
 */
export function reportError(
  error: Error,
  context?: {
    componentStack?: string;
    route?: string;
    requestId?: string;
    [key: string]: unknown;
  }
) {
  const { componentStack, route, requestId, ...extra } = context || {};

  _emit({
    level: "error",
    message: error.message || String(error),
    logger: "bonito.frontend",
    request_id: requestId,
    exception: {
      type: error.name || "Error",
      value: error.message || String(error),
      stacktrace: error.stack || componentStack,
    },
    extra: {
      route: route || (typeof window !== "undefined" ? window.location.pathname : undefined),
      componentStack,
      userAgent: typeof navigator !== "undefined" ? navigator.userAgent : undefined,
      ...extra,
    },
  });
}

/**
 * Track a custom event (non-error) for observability.
 */
export function trackEvent(
  name: string,
  data?: Record<string, unknown>,
  level: "info" | "warning" = "info"
) {
  _emit({
    level,
    message: name,
    logger: "bonito.frontend.event",
    extra: data,
  });
}

/**
 * Install global error handlers. Call once from layout/root component.
 */
export function installGlobalHandlers() {
  if (typeof window === "undefined") return;

  window.addEventListener("error", (event) => {
    if (event.error) {
      reportError(event.error, {
        route: window.location.pathname,
      });
    }
  });

  window.addEventListener("unhandledrejection", (event) => {
    const error =
      event.reason instanceof Error
        ? event.reason
        : new Error(String(event.reason));
    reportError(error, {
      route: window.location.pathname,
    });
  });
}
