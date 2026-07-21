import { NotFoundError, TransportError, UnsupportedVersionError } from "./errors";
import { SUPPORTED_SCHEMA_VERSION } from "./types";

/**
 * Loopback trust domain: only relative same-origin paths are accepted, the
 * error envelope is typed, and every payload's schema_version is gated at
 * this single boundary. No runtime schema validator ships (BRIEF §1).
 */
export async function apiGet<T extends { schema_version: string }>(
  path: `/api/v1/${string}`,
): Promise<T> {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  if (response.status === 404) throw new NotFoundError(path);
  if (!response.ok) throw new TransportError(response.status, path);
  const payload = (await response.json()) as T;
  if (payload.schema_version !== SUPPORTED_SCHEMA_VERSION) {
    throw new UnsupportedVersionError(payload.schema_version, SUPPORTED_SCHEMA_VERSION);
  }
  return payload;
}
