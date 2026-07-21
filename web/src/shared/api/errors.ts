/** Typed client errors. The version gate stops rendering domain data. */

export class UnsupportedVersionError extends Error {
  readonly received: string;
  readonly supported: string;

  constructor(received: string, supported: string) {
    super(`unsupported schema_version ${received}; this build supports ${supported}`);
    this.name = "UnsupportedVersionError";
    this.received = received;
    this.supported = supported;
  }
}

export class NotFoundError extends Error {
  readonly path: string;

  constructor(path: string) {
    super(`no exact match: ${path}`);
    this.name = "NotFoundError";
    this.path = path;
  }
}

export class TransportError extends Error {
  readonly status: number;
  readonly path: string;

  constructor(status: number, path: string) {
    super(`request failed (${status}): ${path}`);
    this.name = "TransportError";
    this.status = status;
    this.path = path;
  }
}
