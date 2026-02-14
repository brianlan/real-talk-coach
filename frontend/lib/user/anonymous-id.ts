const USER_ID_COOKIE_NAME = "rtc_user_id";
const USER_ID_COOKIE_DAYS = 30;
const USER_ID_STORAGE_KEY = "rtc_user_id_backup";
const USER_IP_STORAGE_KEY = "rtc_user_last_ip";

type HeaderValue = string | string[] | null | undefined;
type HeaderSource = Headers | Record<string, HeaderValue>;

export interface AnonymousUserContext {
  ip?: string;
  userAgent?: string;
  headers?: HeaderSource;
}

function isBrowser(): boolean {
  return typeof window !== "undefined" && typeof document !== "undefined";
}

function getCookieValue(name: string): string | null {
  if (!isBrowser()) {
    return null;
  }

  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length !== 2) {
    return null;
  }

  const rawValue = parts.pop()?.split(";").shift();
  if (!rawValue) {
    return null;
  }

  try {
    return decodeURIComponent(rawValue);
  } catch {
    return rawValue;
  }
}

function setCookieValue(name: string, value: string, days: number): void {
  if (!isBrowser()) {
    return;
  }

  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Lax`;
}

function getStorageValue(key: string): string | null {
  if (!isBrowser()) {
    return null;
  }

  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function setStorageValue(key: string, value: string): void {
  if (!isBrowser()) {
    return;
  }

  try {
    window.localStorage.setItem(key, value);
  } catch {
    return;
  }
}

function normalizeIp(ip: string | null | undefined): string | null {
  if (!ip) {
    return null;
  }

  const normalized = ip.trim();
  return normalized.length > 0 ? normalized : null;
}

function getHeaderValue(headers: HeaderSource, key: string): string | null {
  if (typeof Headers !== "undefined" && headers instanceof Headers) {
    return headers.get(key);
  }

  const headerRecord = headers as Record<string, HeaderValue>;

  const lowerKey = key.toLowerCase();
  const match = Object.keys(headerRecord).find(
    (candidate) => candidate.toLowerCase() === lowerKey
  );
  if (!match) {
    return null;
  }

  const value = headerRecord[match];
  if (Array.isArray(value)) {
    return value.join(",");
  }

  return value ?? null;
}

function extractFirstIp(value: string): string | null {
  const firstPart = value.split(",")[0]?.trim();
  if (!firstPart) {
    return null;
  }

  if (firstPart.toLowerCase().startsWith("for=")) {
    const forwardedIp = firstPart.slice(4).trim().replace(/^"|"$/g, "");
    return normalizeIp(forwardedIp);
  }

  return normalizeIp(firstPart.replace(/^"|"$/g, ""));
}

function persistIdentity(userId: string, ip: string | null): void {
  setStorageValue(USER_ID_STORAGE_KEY, userId);
  if (ip) {
    setStorageValue(USER_IP_STORAGE_KEY, ip);
  }
}

/**
 * Generates a UUID v4 identifier for anonymous users.
 */
export function generateAnonymousId(): string {
  return crypto.randomUUID();
}

/**
 * Sets the anonymous user cookie (`rtc_user_id`) with a 30-day expiration.
 */
export function setUserIdCookie(id: string): void {
  setCookieValue(USER_ID_COOKIE_NAME, id, USER_ID_COOKIE_DAYS);
  setStorageValue(USER_ID_STORAGE_KEY, id);
}

/**
 * Extracts the client IP from forwarded header values.
 */
export function getClientIp(headers?: HeaderSource): string | null {
  if (!headers) {
    return null;
  }

  const headerNames = [
    "x-forwarded-for",
    "x-real-ip",
    "cf-connecting-ip",
    "true-client-ip",
    "x-client-ip",
    "forwarded",
  ];

  for (const headerName of headerNames) {
    const rawValue = getHeaderValue(headers, headerName);
    if (!rawValue) {
      continue;
    }

    const ip = extractFirstIp(rawValue);
    if (ip) {
      return ip;
    }
  }

  return null;
}

/**
 * Determines whether a new anonymous ID should be generated.
 *
 * A new ID is generated when the cookie is missing and the resolved IP has changed.
 */
export function shouldGenerateNewId(
  existingId: string | null,
  context: AnonymousUserContext = {}
): boolean {
  if (existingId) {
    return false;
  }

  const storedId = getStorageValue(USER_ID_STORAGE_KEY);
  if (!storedId) {
    return true;
  }

  const currentIp = normalizeIp(context.ip ?? getClientIp(context.headers));
  const previousIp = normalizeIp(getStorageValue(USER_IP_STORAGE_KEY));

  if (!currentIp || !previousIp) {
    return false;
  }

  return currentIp !== previousIp;
}

/**
 * Returns the current anonymous user ID from cookie storage, or creates one when needed.
 */
export function getUserId(context: AnonymousUserContext = {}): string {
  const existingId = getCookieValue(USER_ID_COOKIE_NAME);
  const resolvedIp = normalizeIp(context.ip ?? getClientIp(context.headers));

  if (existingId) {
    persistIdentity(existingId, resolvedIp);
    return existingId;
  }

  const fallbackId = getStorageValue(USER_ID_STORAGE_KEY);
  const nextId = shouldGenerateNewId(existingId, { ...context, ip: resolvedIp ?? undefined })
    ? generateAnonymousId()
    : fallbackId ?? generateAnonymousId();

  setUserIdCookie(nextId);
  persistIdentity(nextId, resolvedIp);

  return nextId;
}
