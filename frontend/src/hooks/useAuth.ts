import { useState, useEffect } from 'react';

/** Keys tried in order when reading the auth token from localStorage */
const TOKEN_KEYS = [
  'mpt_token',
  'token',
  'auth_token',
  'access_token',
  'jwt_token',
  'user_token',
  'mpt-token',
] as const;

const LEARNER_ID_KEYS = ['mpt_learner_id', 'learner_id'] as const;

interface AuthState {
  token: string;
  learnerId: string;
  isSignedIn: boolean;
}

/** Decode the payload section of a JWT without verifying the signature. */
function decodeJwtPayload(jwt: string): Record<string, unknown> | null {
  try {
    const parts = jwt.split('.');
    if (parts.length !== 3) return null;
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const json = atob(base64);
    return JSON.parse(json) as Record<string, unknown>;
  } catch {
    return null;
  }
}

/** Read the stored auth token, trying multiple localStorage keys in order. */
function readStoredToken(): string {
  for (const key of TOKEN_KEYS) {
    const val = localStorage.getItem(key);
    if (val) return val;
  }
  return '';
}

/** Read the stored learner ID from localStorage, or decode it from a JWT. */
function readLearnerId(token: string): string {
  for (const key of LEARNER_ID_KEYS) {
    const val = localStorage.getItem(key);
    if (val) return val;
  }
  if (token) {
    const payload = decodeJwtPayload(token);
    if (payload) {
      const id =
        (payload['learner_id'] as string | undefined) ||
        (payload['sub'] as string | undefined) ||
        (payload['id'] as string | undefined);
      if (id) return String(id);
    }
  }
  return '';
}

/**
 * useAuth — reads auth token and learner ID from localStorage and the URL hash.
 *
 * Supports cross-origin token passing via URL hash fragments:
 *   #token=<jwt>   or   #t=<jwt>
 *
 * When a token is found in the hash it is persisted to localStorage under
 * 'mpt_token' and the fragment is removed from the URL without a history entry.
 */
function useAuth(): AuthState {
  const [auth, setAuth] = useState<AuthState>(() => {
    const token = readStoredToken();
    const learnerId = readLearnerId(token);
    return { token, learnerId, isSignedIn: !!token };
  });

  useEffect(() => {
    /** Parse token from URL hash fragment (#token=... or #t=...) */
    function extractHashToken(): string | null {
      const hash = window.location.hash.slice(1); // strip leading '#'
      if (!hash) return null;
      const params = new URLSearchParams(hash);
      return params.get('token') || params.get('t');
    }

    const hashToken = extractHashToken();

    if (hashToken) {
      // Persist to localStorage and clean up the URL
      localStorage.setItem('mpt_token', hashToken);
      // Remove the hash without adding a history entry
      const cleanUrl =
        window.location.pathname + window.location.search;
      window.history.replaceState(null, '', cleanUrl);

      const learnerId = readLearnerId(hashToken);
      setAuth({ token: hashToken, learnerId, isSignedIn: true });
      return;
    }

    // Fall back to stored token (handles page refreshes)
    const token = readStoredToken();
    const learnerId = readLearnerId(token);
    setAuth({ token, learnerId, isSignedIn: !!token });
  }, []);

  return auth;
}

export default useAuth;
