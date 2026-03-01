/**
 * API/WS base URL helpers for Docker Compose + nginx proxy compatibility.
 *
 * Server-side (Node/SSR): use API_BASE_INTERNAL to reach backend via internal network.
 * Browser-side: use relative URLs (empty base) so nginx proxy handles routing.
 *
 * In Docker:
 * - Set API_BASE_INTERNAL=http://backend:8000 on the frontend container
 * - NEXT_PUBLIC_API_BASE can be empty/omitted; browser will use relative routes
 * - NEXT_PUBLIC_WS_BASE optional; if absent browser uses window.location + /ws
 */

export function getApiBase(): string {
  if (typeof window === "undefined") {
    // Server-side: prefer API_BASE_INTERNAL for Docker internal network
    if (process.env.API_BASE_INTERNAL) {
      return process.env.API_BASE_INTERNAL;
    }
    // Fallback to NEXT_PUBLIC_API_BASE if provided
    if (process.env.NEXT_PUBLIC_API_BASE) {
      return process.env.NEXT_PUBLIC_API_BASE;
    }
    // Local dev default
    return "http://localhost:8000";
  } else {
    // Browser-side: use NEXT_PUBLIC_API_BASE if explicitly set and non-empty
    const explicit = process.env.NEXT_PUBLIC_API_BASE;
    if (explicit && explicit.trim().length > 0) {
      return explicit;
    }
    // Only use local backend fallback when running frontend dev server on port 3000
    const { hostname, port } = window.location;
    if ((hostname === "localhost" || hostname === "127.0.0.1") && port === "3000") {
      return "http://localhost:8000";
    }
    // Otherwise use relative URLs (empty base) so nginx proxy handles routing
    return "";
  }
}

export function getWsBase(): string {
  if (typeof window === "undefined") {
    // Server-side: return empty (WS not used in SSR)
    return "";
  } else {
    // Browser-side: use NEXT_PUBLIC_WS_BASE if provided and non-empty
    const explicit = process.env.NEXT_PUBLIC_WS_BASE;
    if (explicit && explicit.trim().length > 0) {
      return explicit;
    }
    // Only use local WS fallback when running frontend dev server on port 3000
    const { hostname, protocol, port } = window.location;
    if ((hostname === "localhost" || hostname === "127.0.0.1") && port === "3000") {
      const wsProtocol = protocol === "https:" ? "wss:" : "ws:";
      return `${wsProtocol}//localhost:8000/ws`;
    }
    // Otherwise derive from current location (works with nginx proxy)
    const wsProtocol = protocol === "https:" ? "wss:" : "ws:";
    return `${wsProtocol}//${window.location.host}/ws`;
  }
}
